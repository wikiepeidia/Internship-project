"""Fail-closed canonical train/validation input contract for Phase 40.

The module deliberately contains no model-library imports. It validates both
operator-controlled paths lexically before the first file open, then validates
the Phase 39 authority and exact input bytes before parsing any dataset row.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import re
import stat
from typing import BinaryIO, Literal

from pydantic import ConfigDict

from src.data_pipeline.schemas import DatasetRecord


SplitName = Literal["train", "val"]
_LABEL_ORDER = (
    "bank_impersonation",
    "zalo_social_engineering",
    "task_scam",
    "benign",
)
_EXPECTED_DOWNSTREAM_CONTRACT_RELATIVE_PATH = Path(
    ".planning/phases/39-independent-quality-re-judge/39-DOWNSTREAM-DATA-CONTRACT.json"
)
_CANONICAL_DOWNSTREAM_CONTRACT_RELATIVE_PATH = _EXPECTED_DOWNSTREAM_CONTRACT_RELATIVE_PATH
_CANONICAL_TRAIN_RELATIVE_PATH = Path("data/splits/train.jsonl")
_CANONICAL_VAL_RELATIVE_PATH = Path("data/splits/val.jsonl")
_ROW_ID_DOMAIN = b"phase40-snapshot-row-id-v1\0"
_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_REDIRECTING_REPARSE_TAGS = frozenset(
    {
        getattr(stat, "IO_REPARSE_TAG_SYMLINK", 0xA000000C),
        getattr(stat, "IO_REPARSE_TAG_MOUNT_POINT", 0xA0000003),
    }
)
_DATASET_RECORD_KEYS = frozenset(
    {
        "text",
        "label",
        "risk_tier",
        "suspicious_spans",
        "xai_explanation",
        "source",
        "seed_id",
    }
)


class _CanonicalDatasetRecord(DatasetRecord):
    """Deeply immutable, exact-field snapshot form of ``DatasetRecord``."""

    model_config = ConfigDict(frozen=True, extra="forbid")
    suspicious_spans: tuple[str, ...]


def _open_binary(path: Path) -> BinaryIO:
    """Internal opener seam used by reject-before-open fixture tests."""

    return path.open("rb")


@dataclass(frozen=True, slots=True)
class SplitIdentity:
    """Authorized whole-file identity copied from the Phase 39 authority."""

    split_name: SplitName
    relative_path: str
    records: int
    bytes: int
    sha256: str
    label_counts: tuple[tuple[str, int], ...]

    def label_support(self) -> dict[str, int]:
        return dict(self.label_counts)


@dataclass(frozen=True, slots=True)
class HeldOutIdentity:
    """Opaque Phase 41 metadata carried without opening the held-out file."""

    path: str
    records: int
    bytes: int
    sha256: str
    evaluation_phase: int
    touch_policy: str


@dataclass(frozen=True, slots=True)
class CanonicalSnapshotRow:
    """One byte-faithful canonical JSONL record and its stable join identity."""

    split_name: SplitName
    canonical_index: int
    record_bytes: bytes
    record: DatasetRecord
    raw_message: str
    source_row_sha256: str
    snapshot_row_id: str

    @property
    def validation_row_id(self) -> str | None:
        """Return the sole validation join key for validation rows."""

        return self.snapshot_row_id if self.split_name == "val" else None


@dataclass(frozen=True, slots=True)
class CanonicalSplitSnapshot:
    """Immutable sequence and exact authorized bytes for one canonical split."""

    split_name: SplitName
    identity: SplitIdentity
    whole_file_bytes: bytes
    whole_file_sha256: str
    rows: tuple[CanonicalSnapshotRow, ...]

    @property
    def row_ids(self) -> tuple[str, ...]:
        return tuple(row.snapshot_row_id for row in self.rows)

    @property
    def validation_row_ids(self) -> tuple[str, ...]:
        if self.split_name != "val":
            raise ValueError("validation_row_ids are available only on the validation snapshot")
        return self.row_ids


@dataclass(frozen=True, slots=True)
class Phase40DataContract:
    """Authorized train/validation identities, snapshots, and opaque test metadata."""

    ordered_identities: tuple[SplitIdentity, SplitIdentity]
    train_snapshot: CanonicalSplitSnapshot
    validation_snapshot: CanonicalSplitSnapshot
    held_out_test: HeldOutIdentity


def derive_snapshot_row_id(split_name: SplitName, canonical_index: int, source_row_sha256: str) -> str:
    """Derive the exact domain-separated Phase 40 row identity."""

    if split_name not in ("train", "val"):
        raise ValueError("split_name must be train or val")
    if canonical_index < 0:
        raise ValueError("canonical_index must be non-negative")
    if not _SHA256_PATTERN.fullmatch(source_row_sha256):
        raise ValueError("source_row_sha256 must be 64 lowercase hexadecimal characters")
    digest = hashlib.sha256(
        _ROW_ID_DOMAIN
        + split_name.encode("ascii")
        + b"\0"
        + str(canonical_index).encode("ascii")
        + b"\0"
        + bytes.fromhex(source_row_sha256)
    ).hexdigest()
    return f"p40-row-v1-{digest}"


def _lexical_absolute(path: Path, *, repo_root: Path) -> Path:
    root_text = os.path.abspath(os.path.normpath(os.fspath(repo_root)))
    path_text = os.fspath(path)
    if not os.path.isabs(path_text):
        path_text = os.path.join(root_text, path_text)
    return Path(os.path.abspath(os.path.normpath(path_text)))


def _same_lexical_path(left: Path, right: Path) -> bool:
    return os.path.normcase(os.fspath(left)) == os.path.normcase(os.fspath(right))


def _lexical_component_chain(path: Path) -> tuple[Path, ...]:
    """Return absolute path components from the filesystem anchor to ``path``."""

    components: list[Path] = []
    current = path
    while True:
        components.append(current)
        parent = current.parent
        if parent == current:
            break
        current = parent
    return tuple(reversed(components))


def _reject_redirecting_path_components(paths: tuple[Path, ...]) -> None:
    """Reject symbolic links and Windows junctions without following them.

    Components are inspected from the filesystem anchor toward each target so
    a redirecting ancestor is rejected before metadata for any descendant can
    traverse it. Other Windows reparse tags (for example cloud placeholders)
    are not treated as junctions.
    """

    inspected: set[str] = set()
    for path in paths:
        for component in _lexical_component_chain(path):
            component_key = os.path.normcase(os.fspath(component))
            if component_key in inspected:
                continue
            metadata = os.lstat(component)
            reparse_tag = getattr(metadata, "st_reparse_tag", 0)
            if stat.S_ISLNK(metadata.st_mode) or reparse_tag in _REDIRECTING_REPARSE_TAGS:
                raise ValueError(
                    f"canonical Phase 40 path contains a symbolic link or junction: {component}"
                )
            inspected.add(component_key)


def _authorize_paths(train_path: Path, val_path: Path, *, repo_root: Path) -> tuple[Path, Path, Path]:
    root = _lexical_absolute(repo_root, repo_root=Path.cwd())
    train = _lexical_absolute(train_path, repo_root=root)
    val = _lexical_absolute(val_path, repo_root=root)
    expected_train = _lexical_absolute(_CANONICAL_TRAIN_RELATIVE_PATH, repo_root=root)
    expected_val = _lexical_absolute(_CANONICAL_VAL_RELATIVE_PATH, repo_root=root)

    if not _same_lexical_path(train, expected_train):
        raise ValueError("train_path must be the canonical data/splits/train.jsonl path")
    if not _same_lexical_path(val, expected_val):
        raise ValueError("val_path must be the canonical data/splits/val.jsonl path")

    configured_authority = _CANONICAL_DOWNSTREAM_CONTRACT_RELATIVE_PATH
    if (
        configured_authority.is_absolute()
        or configured_authority.as_posix()
        != _EXPECTED_DOWNSTREAM_CONTRACT_RELATIVE_PATH.as_posix()
    ):
        raise RuntimeError("internal Phase 39 authority path no longer has its canonical lexical identity")
    authority = _lexical_absolute(configured_authority, repo_root=root)
    expected_authority = _lexical_absolute(_EXPECTED_DOWNSTREAM_CONTRACT_RELATIVE_PATH, repo_root=root)
    if not _same_lexical_path(authority, expected_authority):
        raise RuntimeError("internal Phase 39 authority path resolved outside its canonical location")
    _reject_redirecting_path_components((authority, train, val))
    return authority, train, val


def _read_bytes(path: Path) -> bytes:
    with _open_binary(path) as handle:
        return handle.read()


def _decode_utf8(payload: bytes, *, description: str) -> str:
    try:
        return payload.decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise ValueError(f"{description} is not valid strict UTF-8") from exc


def _require_mapping(value: object, *, description: str) -> dict[str, object]:
    if not isinstance(value, dict):
        raise ValueError(f"{description} must be a JSON object")
    return value


def _require_non_negative_int(value: object, *, description: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"{description} must be a non-negative integer")
    return value


def _parse_split_identity(authority: dict[str, object], split_name: SplitName) -> SplitIdentity:
    splits = _require_mapping(authority.get("splits"), description="authority splits")
    split = _require_mapping(splits.get(split_name), description=f"authority {split_name} split")
    sha256 = split.get("sha256")
    if not isinstance(sha256, str) or not _SHA256_PATTERN.fullmatch(sha256):
        raise ValueError(f"authority {split_name} SHA-256 is invalid")
    raw_counts = _require_mapping(split.get("label_counts"), description=f"authority {split_name} label_counts")
    if set(raw_counts) != set(_LABEL_ORDER):
        raise ValueError(f"authority {split_name} label support must contain exactly the four locked labels")
    label_counts = tuple(
        (label, _require_non_negative_int(raw_counts[label], description=f"{split_name} support for {label}"))
        for label in _LABEL_ORDER
    )
    relative_path = _CANONICAL_TRAIN_RELATIVE_PATH if split_name == "train" else _CANONICAL_VAL_RELATIVE_PATH
    return SplitIdentity(
        split_name=split_name,
        relative_path=relative_path.as_posix(),
        records=_require_non_negative_int(split.get("records"), description=f"{split_name} record count"),
        bytes=_require_non_negative_int(split.get("bytes"), description=f"{split_name} byte count"),
        sha256=sha256,
        label_counts=label_counts,
    )


def _parse_held_out_identity(authority: dict[str, object]) -> HeldOutIdentity:
    held_out = _require_mapping(authority.get("held_out_test"), description="held_out_test metadata")
    path = held_out.get("path")
    sha256 = held_out.get("sha256")
    touch_policy = held_out.get("touch_policy")
    evaluation_phase = held_out.get("evaluation_phase")
    if path != "data/splits/test.jsonl":
        raise ValueError("held_out_test path must identify the canonical Phase 41 partition")
    if not isinstance(sha256, str) or not _SHA256_PATTERN.fullmatch(sha256):
        raise ValueError("held_out_test SHA-256 is invalid")
    if evaluation_phase != 41:
        raise ValueError("held_out_test evaluation_phase must be 41")
    if not isinstance(touch_policy, str) or not touch_policy.strip():
        raise ValueError("held_out_test touch_policy must be non-empty")
    return HeldOutIdentity(
        path=path,
        records=_require_non_negative_int(held_out.get("records"), description="held-out record count"),
        bytes=_require_non_negative_int(held_out.get("bytes"), description="held-out byte count"),
        sha256=sha256,
        evaluation_phase=evaluation_phase,
        touch_policy=touch_policy,
    )


def _validate_authority_reconciliation(authority: dict[str, object]) -> None:
    source_manifest = _require_mapping(authority.get("source_manifest"), description="source_manifest")
    if source_manifest.get("path") != "data/manifests/manifest.json":
        raise ValueError("source_manifest path is not canonical")
    source_sha = source_manifest.get("sha256")
    if not isinstance(source_sha, str) or not _SHA256_PATTERN.fullmatch(source_sha):
        raise ValueError("source_manifest SHA-256 is invalid")
    source_version = source_manifest.get("version")
    if not isinstance(source_version, str) or not source_version.strip():
        raise ValueError("source_manifest version must be non-empty")

    splits = _require_mapping(authority.get("splits"), description="authority splits")
    split_rows = 0
    aggregate_counts = {label: 0 for label in _LABEL_ORDER}
    for split_name in ("train", "val", "test"):
        split = _require_mapping(splits.get(split_name), description=f"authority {split_name} split")
        split_rows += _require_non_negative_int(split.get("records"), description=f"{split_name} record count")
        raw_counts = _require_mapping(split.get("label_counts"), description=f"{split_name} label_counts")
        if set(raw_counts) != set(_LABEL_ORDER):
            raise ValueError(f"authority {split_name} label support must contain exactly the four locked labels")
        for label in _LABEL_ORDER:
            aggregate_counts[label] += _require_non_negative_int(
                raw_counts[label], description=f"{split_name} support for {label}"
            )

    total_records = _require_non_negative_int(authority.get("total_records"), description="total record count")
    if total_records != split_rows:
        raise ValueError(f"authority total record count mismatch: expected {split_rows}, got {total_records}")
    total_counts = _require_mapping(authority.get("total_label_counts"), description="total_label_counts")
    normalized_totals = {
        label: _require_non_negative_int(total_counts.get(label), description=f"total support for {label}")
        for label in _LABEL_ORDER
    }
    if set(total_counts) != set(_LABEL_ORDER) or normalized_totals != aggregate_counts:
        raise ValueError(
            f"authority total label support mismatch: expected {aggregate_counts}, got {normalized_totals}"
        )
    if sum(aggregate_counts.values()) != total_records:
        raise ValueError("authority label support does not sum to total_records")

    test_split = _require_mapping(splits.get("test"), description="authority test split")
    held_out = _require_mapping(authority.get("held_out_test"), description="held_out_test metadata")
    for field in ("records", "bytes", "sha256"):
        if held_out.get(field) != test_split.get(field):
            raise ValueError(f"held_out_test {field} does not match splits.test metadata")


def _parse_authority(payload: bytes) -> tuple[SplitIdentity, SplitIdentity, HeldOutIdentity]:
    text = _decode_utf8(payload, description="Phase 39 downstream authority")
    try:
        authority = _require_mapping(
            json.loads(text, object_pairs_hook=_reject_duplicate_json_keys),
            description="Phase 39 downstream authority",
        )
    except json.JSONDecodeError as exc:
        raise ValueError("Phase 39 downstream authority is not valid JSON") from exc
    if authority.get("schema_version") != "phase39-downstream-data-contract-v1":
        raise ValueError("unsupported Phase 39 downstream authority schema_version")
    _validate_authority_reconciliation(authority)
    boundary = _require_mapping(authority.get("phase40_training_boundary"), description="phase40_training_boundary")
    if boundary.get("allowed_splits") != ["train", "val"] or boundary.get("forbidden_split") != "test":
        raise ValueError("Phase 39 authority does not enforce the train/validation-only Phase 40 boundary")
    return (
        _parse_split_identity(authority, "train"),
        _parse_split_identity(authority, "val"),
        _parse_held_out_identity(authority),
    )


def _verify_whole_file(payload: bytes, identity: SplitIdentity) -> None:
    if not payload:
        raise ValueError(f"{identity.split_name} split is empty")
    if len(payload) != identity.bytes:
        raise ValueError(
            f"{identity.split_name} byte count mismatch: expected {identity.bytes}, got {len(payload)}"
        )
    digest = hashlib.sha256(payload).hexdigest()
    if digest != identity.sha256:
        raise ValueError(
            f"{identity.split_name} SHA-256 mismatch: expected {identity.sha256}, got {digest}"
        )


def _frame_records(payload: bytes, *, split_name: SplitName) -> tuple[bytes, ...]:
    _decode_utf8(payload, description=f"{split_name} split")
    framed: list[bytes] = []
    cursor = 0
    while cursor < len(payload):
        newline_index = payload.find(b"\n", cursor)
        if newline_index < 0:
            record_bytes = payload[cursor:]
            cursor = len(payload)
        else:
            record_bytes = payload[cursor:newline_index]
            cursor = newline_index + 1
            if record_bytes.endswith(b"\r"):
                record_bytes = record_bytes[:-1]
        if not record_bytes:
            raise ValueError(f"{split_name} split contains a blank JSONL record")
        if b"\r" in record_bytes:
            raise ValueError(f"{split_name} split contains a bare CR byte")
        framed.append(record_bytes)
    if not framed:
        raise ValueError(f"{split_name} split is empty")
    return tuple(framed)


def _build_snapshot(payload: bytes, identity: SplitIdentity) -> CanonicalSplitSnapshot:
    rows: list[CanonicalSnapshotRow] = []
    for index, record_bytes in enumerate(_frame_records(payload, split_name=identity.split_name)):
        record_text = _decode_utf8(record_bytes, description=f"{identity.split_name} record {index}")
        try:
            parsed_json = json.loads(record_text, object_pairs_hook=_reject_duplicate_json_keys)
            if not isinstance(parsed_json, dict):
                raise ValueError("record must be a JSON object")
            if set(parsed_json) != _DATASET_RECORD_KEYS:
                missing = sorted(_DATASET_RECORD_KEYS.difference(parsed_json))
                extra = sorted(set(parsed_json).difference(_DATASET_RECORD_KEYS))
                raise ValueError(f"record fields mismatch; missing={missing}, extra={extra}")
            record = _CanonicalDatasetRecord.model_validate(parsed_json)
        except (json.JSONDecodeError, ValueError) as exc:
            raise ValueError(f"{identity.split_name} record {index} violates DatasetRecord schema: {exc}") from exc
        source_sha256 = hashlib.sha256(record_bytes).hexdigest()
        rows.append(
            CanonicalSnapshotRow(
                split_name=identity.split_name,
                canonical_index=index,
                record_bytes=record_bytes,
                record=record,
                raw_message=record.text,
                source_row_sha256=source_sha256,
                snapshot_row_id=derive_snapshot_row_id(identity.split_name, index, source_sha256),
            )
        )

    if len(rows) != identity.records:
        raise ValueError(
            f"{identity.split_name} record count mismatch: expected {identity.records}, got {len(rows)}"
        )
    support = Counter(row.record.label for row in rows)
    expected_support = identity.label_support()
    actual_support = {label: support.get(label, 0) for label in _LABEL_ORDER}
    if actual_support != expected_support:
        raise ValueError(
            f"{identity.split_name} label support mismatch: expected {expected_support}, got {actual_support}"
        )
    return CanonicalSplitSnapshot(
        split_name=identity.split_name,
        identity=identity,
        whole_file_bytes=payload,
        whole_file_sha256=hashlib.sha256(payload).hexdigest(),
        rows=tuple(rows),
    )


def _reject_duplicate_json_keys(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def preflight_phase40_inputs(
    train_path: Path,
    val_path: Path,
    *,
    repo_root: Path,
) -> Phase40DataContract:
    """Authorize and materialize the canonical Phase 40 train/validation snapshots.

    Both caller-controlled paths and the private authority path are validated
    lexically before the first open. The held-out partition is never opened.
    """

    authority_path, canonical_train, canonical_val = _authorize_paths(
        Path(train_path), Path(val_path), repo_root=Path(repo_root)
    )
    train_identity, val_identity, held_out = _parse_authority(_read_bytes(authority_path))
    train_payload = _read_bytes(canonical_train)
    val_payload = _read_bytes(canonical_val)
    _verify_whole_file(train_payload, train_identity)
    _verify_whole_file(val_payload, val_identity)

    train_snapshot = _build_snapshot(train_payload, train_identity)
    val_snapshot = _build_snapshot(val_payload, val_identity)
    train_seeds = {row.record.seed_id for row in train_snapshot.rows}
    val_seeds = {row.record.seed_id for row in val_snapshot.rows}
    overlap = sorted(train_seeds.intersection(val_seeds))
    if overlap:
        raise ValueError(f"train/validation seed overlap detected: {', '.join(overlap[:5])}")

    return Phase40DataContract(
        ordered_identities=(train_identity, val_identity),
        train_snapshot=train_snapshot,
        validation_snapshot=val_snapshot,
        held_out_test=held_out,
    )
