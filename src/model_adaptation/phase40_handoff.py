"""Deterministic, validation-only Phase 40 handoff and review contracts.

This module deliberately has no model, CUDA, package-install, or network side
effects.  It moves only already-authorized train/validation bytes and binds all
review work to the immutable validation row identities established by the
Phase 40 input contract.
"""

from __future__ import annotations

import ast
from dataclasses import asdict, dataclass
import hashlib
import io
import json
import math
import os
from pathlib import Path, PurePosixPath
import re
import stat
import tempfile
from typing import Any, BinaryIO, Callable, Iterable, Literal, Mapping, Sequence
import zipfile
import zlib

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from src.model_adaptation.phase40_contract import (
    CanonicalSplitSnapshot,
    HeldOutIdentity,
    Phase40DataContract,
    SplitIdentity,
    _build_snapshot,
    _reject_redirecting_path_components,
)
from src.model_adaptation.phase40_metrics import (
    LABEL_ORDER,
    RISKY_LABELS,
    RISKY_RECALL_FLOORS,
    CheckpointSelection,
    Phase40MetricResult,
    Phase40PredictionRow,
    PredictionState,
    evaluate_phase40_predictions,
    select_phase40_checkpoint,
)
from src.model_adaptation.phase40_evidence import (
    AcceleratorIdentity,
    EvidenceStatus,
    QwenConfigComparison,
    QuantizationProofEvidence,
    ResumeControlledConfig,
    RunEvidence,
    TransferAuthorityEvidence,
    compare_qwen_configs,
    compute_resume_digest,
    verify_phase40_bundle,
)
from src.model_adaptation.phase40_graphs import (
    GraphProvenance,
    GraphRenderer,
    render_phase40_graphs,
)
from src.model_adaptation.phase40_modes import (
    AdaptationMode,
    ModelFamily,
    ResolvedQwenMode,
    RunKind,
)
from src.model_adaptation.registry import build_model_checksum


PHASE40_INPUT_SCHEMA_VERSION = "phase40-input-bundle-v1"
PHASE40_SOURCE_SCHEMA_VERSION = "phase40-source-bundle-v1"
PHASE40_RUN_REQUEST_SCHEMA_VERSION = "phase40-full-run-request-v1"
PHASE40_REVIEW_QUEUE_SCHEMA_VERSION = "phase40-review-queue-v1"
PHASE40_HUMAN_REVIEW_SCHEMA_VERSION = "phase40-human-review-v1"
PHASE40_COMPARISON_SCHEMA_VERSION = "phase40-comparison-v2"
PHASE40_SCOPE_AMENDMENT_SCHEMA_VERSION = "phase40-two-full-model-scope-amendment-v1"
PHASE40_SNAPSHOT_ID_VERSION = "phase40-snapshot-row-id-v1"

INPUT_MEMBER_NAMES = (
    "phase40-input-manifest.json",
    "train.jsonl",
    "val.jsonl",
)
FIXED_INPUT_REPOSITORY_PATH = "data/models/phase40/input/phase40-train-validation.zip"
FIXED_INPUT_DRIVE_PATH = "/content/drive/MyDrive/internship-phase40/phase40-train-validation.zip"
FIXED_INPUT_EXTRACTION_ROOT = "/content/phase40-input-v1"
FIXED_SOURCE_ARCHIVE_PATH = "data/models/phase40/source/phase40-source.zip"
FIXED_SOURCE_INVENTORY_PATH = "data/models/phase40/source/phase40-source-manifest.json"
FIXED_RUN_REQUEST_PATH = "data/models/phase40/full-run-request.json"
FIXED_SCOPE_AMENDMENT_PATH = "data/models/phase40/two-full-model-scope-amendment.json"
FIXED_MATCHED_QWEN_CONFIG_PATH = "data/models/phase40/matched-qwen-config.json"
FIXED_PHOBERT_CONFIG_PATH = "data/models/phase40/phobert-config.json"
FIXED_GGUF_TOOL_AUTHORITY_PATH = "data/models/phase40/gguf-tool-authority.json"
FIXED_RETURNED_ROOTS = (
    "data/models/phase40/full/qwen-lora",
    "data/models/phase40/full/qwen-qlora",
    "data/models/phase40/full/phobert",
)
FIXED_ACTIVE_RETURNED_ROOTS = FIXED_RETURNED_ROOTS[1:]
FIXED_LORA_PROBE_ROOT = (
    "data/models/phase40/probes/rtx5050-local-decision/lora-retry-1"
)
FIXED_LORA_PROBE_FILES = (
    "outcome.json",
    "telemetry.jsonl",
    "optimizer-events.jsonl",
    "quantization-proof.json",
    "discard-receipt.json",
)
PACKAGE_CANDIDATES = ("bitsandbytes==0.50.1", "matplotlib==3.11.1")
PINNED_QWEN_MODEL_ID = "Qwen/Qwen3-4B-Instruct-2507"
PINNED_QWEN_REVISION = "cdbee75f17c01a7cc42f958dc650907174af0554"
PINNED_PHOBERT_MODEL_ID = "vinai/phobert-base-v2"
PINNED_PHOBERT_REVISION = "e966aac8cb889325e073aa5f28ff70aca4dbc8c3"
REQUIRED_FULL_BUNDLE_FILES = tuple(
    sorted(
        (
            "adapter-or-model",
            "curves/graph-provenance.json",
            "curves/loss-curves.png",
            "curves/normalized-loss-curves.json",
            "events.jsonl",
            "predictions.json",
            "resolved-config.json",
            "run-evidence.json",
            "trainer_state.json",
            "validation-metrics.json",
        )
    )
)

# The executable source transfer is intentionally explicit.  Plan 40-03 may
# append its PhoBERT files before the immutable request is frozen, but callers
# cannot substitute or discover arbitrary repository files.
PHASE40_SOURCE_ALLOWLIST = (
    "pyproject.toml",
    "src/__init__.py",
    "src/config/__init__.py",
    "src/config/settings.py",
    "src/data_pipeline/__init__.py",
    "src/data_pipeline/schemas.py",
    "src/model_adaptation/__init__.py",
    "src/model_adaptation/catalog.py",
    "src/model_adaptation/data.py",
    "src/model_adaptation/phase40_callbacks.py",
    "src/model_adaptation/phase40_colab_prepare.py",
    "src/model_adaptation/phase40_contract.py",
    "src/model_adaptation/phase40_evidence.py",
    "src/model_adaptation/phase40_graphs.py",
    "src/model_adaptation/phase40_gguf.py",
    "src/model_adaptation/phase40_handoff.py",
    "src/model_adaptation/phase40_metrics.py",
    "src/model_adaptation/phase40_modes.py",
    "src/model_adaptation/phase40_notebooks.py",
    "src/model_adaptation/phase40_operator.py",
    "src/model_adaptation/phobert_training.py",
    "src/model_adaptation/pilot.py",
    "src/model_adaptation/prompts.py",
    "src/model_adaptation/registry.py",
    "src/model_adaptation/schemas.py",
    "src/model_adaptation/training.py",
    "src/runtime/__init__.py",
    "src/runtime/contracts.py",
)
# Additive authority for the amended comparison command.  Keep the historical
# training allowlist above byte-for-byte stable because source-runtime-v3 and
# the frozen full-run request are already bound to it.
PHASE40_COMPARISON_FINALIZER_ENTRYPOINTS = ("src/model_adaptation/cli.py",)
PHASE40_COMPARISON_FINALIZER_SOURCE_ALLOWLIST = (
    "pyproject.toml",
    "src/__init__.py",
    "src/config/__init__.py",
    "src/config/settings.py",
    "src/data_pipeline/__init__.py",
    "src/data_pipeline/processing/__init__.py",
    "src/data_pipeline/processing/normalizer.py",
    "src/data_pipeline/schemas.py",
    "src/model_adaptation/__init__.py",
    "src/model_adaptation/catalog.py",
    "src/model_adaptation/cli.py",
    "src/model_adaptation/convert.py",
    "src/model_adaptation/data.py",
    "src/model_adaptation/doctor.py",
    "src/model_adaptation/explanation_review.py",
    "src/model_adaptation/phase40_callbacks.py",
    "src/model_adaptation/phase40_contract.py",
    "src/model_adaptation/phase40_evidence.py",
    "src/model_adaptation/phase40_graphs.py",
    "src/model_adaptation/phase40_handoff.py",
    "src/model_adaptation/phase40_metrics.py",
    "src/model_adaptation/phase40_modes.py",
    "src/model_adaptation/phase40_notebooks.py",
    "src/model_adaptation/pilot.py",
    "src/model_adaptation/prompts.py",
    "src/model_adaptation/registry.py",
    "src/model_adaptation/release_evaluation.py",
    "src/model_adaptation/release_gates.py",
    "src/model_adaptation/release_readiness.py",
    "src/model_adaptation/schemas.py",
    "src/model_adaptation/training.py",
    "src/runtime/__init__.py",
    "src/runtime/analyzers/__init__.py",
    "src/runtime/analyzers/accelerated.py",
    "src/runtime/analyzers/base.py",
    "src/runtime/analyzers/gguf.py",
    "src/runtime/analyzers/heuristic.py",
    "src/runtime/analyzers/local_model.py",
    "src/runtime/analyzers/rules.py",
    "src/runtime/contracts.py",
    "src/runtime/service.py",
)

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_SAFE_RUN_ID_RE = re.compile(r"^[a-z0-9][a-z0-9._-]{0,95}$")
_SECRET_RE = re.compile(
    r"(?i)(api[_-]?key|authorization|bearer|credential|password|secret|token)"
)
_WINDOWS_ABSOLUTE_RE = re.compile(r"^[A-Za-z]:[\\/]")
_SLICE_ORDER = (
    "invalid_output",
    "risky_to_benign",
    "zalo_involved_misclassification",
    "benign_to_risky",
    "risky_cross_confusion",
    "correct_calibration_sample",
)
ReviewSlice = Literal[
    "invalid_output",
    "risky_to_benign",
    "zalo_involved_misclassification",
    "benign_to_risky",
    "risky_cross_confusion",
    "correct_calibration_sample",
]


def _canonical_json_bytes(value: object) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        + "\n"
    ).encode("utf-8")


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _require_sha256(value: str, *, description: str) -> str:
    if not isinstance(value, str) or not _SHA256_RE.fullmatch(value):
        raise ValueError(f"{description} must be 64 lowercase hexadecimal characters")
    return value


def _lexical_absolute(path: Path) -> Path:
    return Path(os.path.abspath(os.path.normpath(os.fspath(path))))


def _trusted_repo_root(repo_root: Path) -> Path:
    """Return an existing lexical root after rejecting redirecting components."""

    root = _lexical_absolute(Path(repo_root))
    _reject_redirecting_path_components((root,))
    if not root.is_dir() or root.is_symlink():
        raise ValueError("Phase 40 repository root is missing or redirects")
    return root


def _atomic_write_bytes(path: Path, payload: bytes) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    handle = tempfile.NamedTemporaryFile(
        mode="wb",
        prefix=f".{path.name}.",
        suffix=".tmp",
        dir=path.parent,
        delete=False,
    )
    temporary = Path(handle.name)
    try:
        with handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()
    if path.read_bytes() != payload:
        raise RuntimeError(f"atomic write read-back mismatch: {path}")
    return path


def _write_frozen_bytes(path: Path, payload: bytes) -> Path:
    """Create an immutable claim artifact, accepting only byte-identical replay."""

    path = Path(path)
    if path.exists():
        if not path.is_file() or path.is_symlink() or path.read_bytes() != payload:
            raise RuntimeError(f"frozen artifact already exists with different content: {path}")
        return path
    return _atomic_write_bytes(path, payload)


def _safe_relative_path(value: str, *, description: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{description} must be non-empty")
    if "\\" in value or _WINDOWS_ABSOLUTE_RE.match(value):
        raise ValueError(f"{description} must use a repository-relative POSIX path")
    path = PurePosixPath(value)
    if path.is_absolute() or any(part in ("", ".", "..") for part in path.parts):
        raise ValueError(f"{description} must be a normalized repository-relative path")
    return path.as_posix()


def _safe_archive_member(value: str) -> str:
    normalized = _safe_relative_path(value, description="archive member")
    lowered_parts = tuple(part.casefold() for part in PurePosixPath(normalized).parts)
    if any(part == "test" or part.startswith("test.") or part.startswith("test_") for part in lowered_parts):
        raise ValueError("archive member must not be held-out/test-like")
    return normalized


def _zip_info(name: str) -> zipfile.ZipInfo:
    info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
    info.compress_type = zipfile.ZIP_STORED
    info.create_system = 3
    info.external_attr = 0o100644 << 16
    info.flag_bits = 0
    return info


def _deterministic_zip(members: Sequence[tuple[str, bytes]]) -> bytes:
    names = tuple(name for name, _ in members)
    if names != tuple(sorted(names)) or len(names) != len(set(names)):
        raise ValueError("archive members must be unique and sorted")
    output = io.BytesIO()
    with zipfile.ZipFile(output, mode="w", compression=zipfile.ZIP_STORED) as archive:
        for name, payload in members:
            archive.writestr(_zip_info(_safe_archive_member(name)), payload)
    return output.getvalue()


def _path_is_redirect(path: Path) -> bool:
    metadata = os.lstat(path)
    reparse_tag = getattr(metadata, "st_reparse_tag", 0)
    return stat.S_ISLNK(metadata.st_mode) or reparse_tag in {
        getattr(stat, "IO_REPARSE_TAG_SYMLINK", 0xA000000C),
        getattr(stat, "IO_REPARSE_TAG_MOUNT_POINT", 0xA0000003),
    }


def _contract_identity(contract: Phase40DataContract) -> str:
    payload = {
        "train": asdict(contract.train_snapshot.identity),
        "val": asdict(contract.validation_snapshot.identity),
        "held_out_opaque": asdict(contract.held_out_test),
    }
    return _sha256(_canonical_json_bytes(payload))


def _ordered_row_ids_sha256(snapshot: CanonicalSplitSnapshot) -> str:
    digest = hashlib.sha256(b"phase40-ordered-row-ids-v1\0")
    for row_id in snapshot.row_ids:
        digest.update(row_id.encode("ascii"))
        digest.update(b"\n")
    return digest.hexdigest()


class InputDataMember(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    logical_name: Literal["train", "val"]
    member_name: Literal["train.jsonl", "val.jsonl"]
    records: int = Field(ge=1)
    bytes: int = Field(ge=1)
    sha256: str
    crc32: str
    ordered_row_ids_sha256: str

    @field_validator("sha256", "ordered_row_ids_sha256")
    @classmethod
    def validate_hash(cls, value: str) -> str:
        return _require_sha256(value, description="input member hash")

    @field_validator("crc32")
    @classmethod
    def validate_crc32(cls, value: str) -> str:
        if not re.fullmatch(r"[0-9a-f]{8}", value):
            raise ValueError("input member CRC32 must be eight lowercase hexadecimal characters")
        return value

    @model_validator(mode="after")
    def align_name(self) -> "InputDataMember":
        if self.member_name != f"{self.logical_name}.jsonl":
            raise ValueError("input member logical and archive names do not align")
        return self


class Phase40InputManifest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["phase40-input-bundle-v1"] = PHASE40_INPUT_SCHEMA_VERSION
    members: tuple[str, str, str] = INPUT_MEMBER_NAMES
    data_members: tuple[InputDataMember, InputDataMember]
    phase39_data_contract_sha256: str
    held_out_opaque: HeldOutIdentity
    snapshot_row_id_version: Literal["phase40-snapshot-row-id-v1"] = PHASE40_SNAPSHOT_ID_VERSION

    @field_validator("phase39_data_contract_sha256")
    @classmethod
    def validate_hash(cls, value: str) -> str:
        return _require_sha256(value, description="Phase 39 data contract hash")

    @model_validator(mode="after")
    def validate_inventory(self) -> "Phase40InputManifest":
        if self.members != INPUT_MEMBER_NAMES:
            raise ValueError("input archive must contain exactly the three fixed members")
        if tuple(member.logical_name for member in self.data_members) != ("train", "val"):
            raise ValueError("input data members must be ordered train then val")
        return self


class InputBundleReference(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    repository_relative_path: str = FIXED_INPUT_REPOSITORY_PATH
    archive_sha256: str
    manifest_sha256: str
    members: tuple[str, str, str] = INPUT_MEMBER_NAMES
    data_members: tuple[InputDataMember, InputDataMember]
    phase39_data_contract_sha256: str
    held_out_opaque: HeldOutIdentity
    snapshot_row_id_version: Literal["phase40-snapshot-row-id-v1"] = PHASE40_SNAPSHOT_ID_VERSION
    drive_path: str = FIXED_INPUT_DRIVE_PATH
    extraction_root: str = FIXED_INPUT_EXTRACTION_ROOT

    @field_validator("archive_sha256", "manifest_sha256", "phase39_data_contract_sha256")
    @classmethod
    def validate_hash(cls, value: str) -> str:
        return _require_sha256(value, description="input bundle hash")

    @model_validator(mode="after")
    def validate_fixed_contract(self) -> "InputBundleReference":
        if self.repository_relative_path != FIXED_INPUT_REPOSITORY_PATH:
            raise ValueError("input bundle repository path is not canonical")
        if self.drive_path != FIXED_INPUT_DRIVE_PATH:
            raise ValueError("input bundle Drive path is not canonical")
        if self.extraction_root != FIXED_INPUT_EXTRACTION_ROOT:
            raise ValueError("input bundle extraction root is not canonical")
        if self.members != INPUT_MEMBER_NAMES:
            raise ValueError("input bundle member set is not canonical")
        if tuple(member.logical_name for member in self.data_members) != ("train", "val"):
            raise ValueError("input bundle data members must be train then val")
        return self


@dataclass(frozen=True, slots=True)
class BuiltInputBundle:
    archive_path: Path
    reference: InputBundleReference
    manifest_bytes: bytes


def _input_manifest(contract: Phase40DataContract) -> Phase40InputManifest:
    members = tuple(
        InputDataMember(
            logical_name=snapshot.split_name,
            member_name=f"{snapshot.split_name}.jsonl",
            records=snapshot.identity.records,
            bytes=len(snapshot.whole_file_bytes),
            sha256=snapshot.whole_file_sha256,
            crc32=f"{zlib.crc32(snapshot.whole_file_bytes) & 0xFFFFFFFF:08x}",
            ordered_row_ids_sha256=_ordered_row_ids_sha256(snapshot),
        )
        for snapshot in (contract.train_snapshot, contract.validation_snapshot)
    )
    return Phase40InputManifest(
        data_members=members,
        phase39_data_contract_sha256=_contract_identity(contract),
        held_out_opaque=contract.held_out_test,
    )


def build_phase40_input_bundle(
    contract: Phase40DataContract,
    output_path: Path,
    *,
    repo_root: Path | None = None,
) -> BuiltInputBundle:
    """Write the exact authorized train/validation bytes to a normalized ZIP."""

    if not isinstance(contract, Phase40DataContract):
        raise TypeError("input bundle construction requires a Phase40DataContract")
    if contract.train_snapshot.split_name != "train" or contract.validation_snapshot.split_name != "val":
        raise ValueError("input contract snapshots must be ordered train then val")
    output_path = Path(output_path)
    normalized_parts = tuple(part.casefold() for part in output_path.parts)
    fixed_parts = tuple(part.casefold() for part in PurePosixPath(FIXED_INPUT_REPOSITORY_PATH).parts)
    if len(normalized_parts) < len(fixed_parts) or normalized_parts[-len(fixed_parts) :] != fixed_parts:
        raise ValueError("input bundle output path must end at the canonical repository location")
    if repo_root is not None:
        expected = Path(os.path.abspath(os.path.normpath(os.fspath(Path(repo_root) / FIXED_INPUT_REPOSITORY_PATH))))
        supplied = Path(os.path.abspath(os.path.normpath(os.fspath(output_path))))
        if supplied != expected:
            raise ValueError("input bundle output path is not the canonical repository location")
    manifest = _input_manifest(contract)
    manifest_bytes = _canonical_json_bytes(manifest.model_dump(mode="json"))
    archive_bytes = _deterministic_zip(
        (
            ("phase40-input-manifest.json", manifest_bytes),
            ("train.jsonl", contract.train_snapshot.whole_file_bytes),
            ("val.jsonl", contract.validation_snapshot.whole_file_bytes),
        )
    )
    output_path = _atomic_write_bytes(output_path, archive_bytes)
    reference = InputBundleReference(
        archive_sha256=_sha256(archive_bytes),
        manifest_sha256=_sha256(manifest_bytes),
        data_members=manifest.data_members,
        phase39_data_contract_sha256=manifest.phase39_data_contract_sha256,
        held_out_opaque=manifest.held_out_opaque,
    )
    return BuiltInputBundle(output_path, reference, manifest_bytes)


def _default_zip_member_opener(
    archive: zipfile.ZipFile,
    member_name: str,
) -> BinaryIO:
    return archive.open(member_name, "r")


def _authorized_input_archive_path(
    archive_path: Path,
    reference: InputBundleReference,
    *,
    repo_root: Path,
) -> Path:
    supplied = Path(os.path.abspath(os.path.normpath(os.fspath(archive_path))))
    local = Path(
        os.path.abspath(
            os.path.normpath(os.fspath(Path(repo_root) / reference.repository_relative_path))
        )
    )
    drive = Path(reference.drive_path)
    if supplied != local and os.fspath(archive_path) != reference.drive_path and supplied != drive:
        raise ValueError("input archive path is not request-bound")
    return supplied


def _validate_zip_directory(archive: zipfile.ZipFile) -> None:
    infos = archive.infolist()
    names = tuple(info.filename for info in infos)
    if names != INPUT_MEMBER_NAMES or len(names) != len(set(names)):
        raise ValueError("input archive must contain exactly the sorted three-member inventory")
    for info in infos:
        _safe_archive_member(info.filename)
        unix_mode = (info.external_attr >> 16) & 0o170000
        if info.is_dir() or info.filename.endswith("/") or unix_mode == stat.S_IFLNK:
            raise ValueError("input archive cannot contain directories or symbolic links")
        if info.compress_type != zipfile.ZIP_STORED:
            raise ValueError("input archive must use deterministic stored members")


def verify_phase40_input_bundle(
    archive_path: Path,
    reference: InputBundleReference,
    *,
    repo_root: Path,
    extraction_root: Path | None = None,
    member_opener: Callable[[zipfile.ZipFile, str], BinaryIO] = _default_zip_member_opener,
    materialize: bool = True,
) -> Phase40DataContract:
    """Verify structure/hashes before opening either JSONL member, then extract."""

    if not isinstance(reference, InputBundleReference):
        reference = InputBundleReference.model_validate(reference)
    authorized = _authorized_input_archive_path(
        Path(archive_path), reference, repo_root=Path(repo_root)
    )
    archive_bytes = authorized.read_bytes()
    if _sha256(archive_bytes) != reference.archive_sha256:
        raise ValueError("input archive SHA-256 mismatch")

    with zipfile.ZipFile(io.BytesIO(archive_bytes), mode="r") as archive:
        _validate_zip_directory(archive)
        manifest_bytes = archive.read("phase40-input-manifest.json")
        if _sha256(manifest_bytes) != reference.manifest_sha256:
            raise ValueError("input manifest SHA-256 mismatch")
        try:
            manifest = Phase40InputManifest.model_validate_json(manifest_bytes)
        except Exception as exc:
            raise ValueError("input manifest schema validation failed") from exc
        if manifest.members != reference.members:
            raise ValueError("input manifest member inventory differs from the request")
        if manifest.data_members != reference.data_members:
            raise ValueError("input manifest data identities differ from the request")
        if manifest.phase39_data_contract_sha256 != reference.phase39_data_contract_sha256:
            raise ValueError("input manifest Phase 39 identity differs from the request")
        if manifest.held_out_opaque != reference.held_out_opaque:
            raise ValueError("input manifest opaque held-out metadata differs from the request")

        info_by_name = {info.filename: info for info in archive.infolist()}
        for member in manifest.data_members:
            info = info_by_name[member.member_name]
            if (
                info.file_size != member.bytes
                or f"{info.CRC & 0xFFFFFFFF:08x}" != member.crc32
            ):
                raise ValueError(
                    f"input member central-directory identity mismatch: {member.member_name}"
                )

        payloads: dict[str, bytes] = {}
        for member in manifest.data_members:
            with member_opener(archive, member.member_name) as handle:
                payload = handle.read()
            if len(payload) != member.bytes or _sha256(payload) != member.sha256:
                raise ValueError(f"input member identity mismatch: {member.member_name}")
            payloads[member.logical_name] = payload

    train_identity = SplitIdentity(
        "train",
        "data/splits/train.jsonl",
        reference.data_members[0].records,
        reference.data_members[0].bytes,
        reference.data_members[0].sha256,
        (),
    )
    val_identity = SplitIdentity(
        "val",
        "data/splits/val.jsonl",
        reference.data_members[1].records,
        reference.data_members[1].bytes,
        reference.data_members[1].sha256,
        (),
    )
    # The archive manifest intentionally omits parsed label supports.  Rebuild
    # byte-faithful snapshots with temporary support identities computed from
    # the locked records, then prove the ordered row-ID digests.
    train_snapshot = _snapshot_from_bundle_bytes(payloads["train"], train_identity)
    val_snapshot = _snapshot_from_bundle_bytes(payloads["val"], val_identity)
    if _ordered_row_ids_sha256(train_snapshot) != reference.data_members[0].ordered_row_ids_sha256:
        raise ValueError("train snapshot row-ID sequence mismatch")
    if _ordered_row_ids_sha256(val_snapshot) != reference.data_members[1].ordered_row_ids_sha256:
        raise ValueError("validation snapshot row-ID sequence mismatch")

    if materialize:
        target_root = Path(extraction_root or reference.extraction_root)
        if os.fspath(target_root).replace("\\", "/") != reference.extraction_root:
            raise ValueError("input extraction root is not request-bound")
        _atomic_write_bytes(target_root / "train.jsonl", payloads["train"])
        _atomic_write_bytes(target_root / "val.jsonl", payloads["val"])

    return Phase40DataContract(
        ordered_identities=(train_snapshot.identity, val_snapshot.identity),
        train_snapshot=train_snapshot,
        validation_snapshot=val_snapshot,
        held_out_test=reference.held_out_opaque,
    )


def _snapshot_from_bundle_bytes(payload: bytes, identity: SplitIdentity) -> CanonicalSplitSnapshot:
    from collections import Counter
    from src.model_adaptation.phase40_contract import _frame_records
    from src.data_pipeline.schemas import DatasetRecord

    records = []
    for record_bytes in _frame_records(payload, split_name=identity.split_name):
        records.append(DatasetRecord.model_validate_json(record_bytes))
    counts = Counter(record.label for record in records)
    supported_identity = SplitIdentity(
        identity.split_name,
        identity.relative_path,
        identity.records,
        identity.bytes,
        identity.sha256,
        tuple((label, counts.get(label, 0)) for label in LABEL_ORDER),
    )
    return _build_snapshot(payload, supported_identity)


class SourceInventoryEntry(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    path: str
    # Empty package markers such as ``src/__init__.py`` are valid executable
    # source members.  Their SHA-256 still binds the exact zero-byte payload.
    bytes: int = Field(ge=0)
    sha256: str

    @field_validator("path")
    @classmethod
    def validate_path(cls, value: str) -> str:
        return _safe_relative_path(value, description="source path")

    @field_validator("sha256")
    @classmethod
    def validate_hash(cls, value: str) -> str:
        return _require_sha256(value, description="source file hash")


class SourceInventory(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["phase40-source-bundle-v1"] = PHASE40_SOURCE_SCHEMA_VERSION
    archive_sha256: str
    files: tuple[SourceInventoryEntry, ...]

    @field_validator("archive_sha256")
    @classmethod
    def validate_hash(cls, value: str) -> str:
        return _require_sha256(value, description="source archive hash")

    @model_validator(mode="after")
    def validate_files(self) -> "SourceInventory":
        paths = tuple(entry.path for entry in self.files)
        if not paths or paths != tuple(sorted(paths)) or len(paths) != len(set(paths)):
            raise ValueError("source inventory must be non-empty, unique, and sorted")
        return self


class SourceBundleReference(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    repository_relative_archive_path: str = FIXED_SOURCE_ARCHIVE_PATH
    archive_sha256: str
    repository_relative_inventory_path: str = FIXED_SOURCE_INVENTORY_PATH
    inventory_sha256: str
    files: tuple[SourceInventoryEntry, ...]

    @field_validator("archive_sha256", "inventory_sha256")
    @classmethod
    def validate_hash(cls, value: str) -> str:
        return _require_sha256(value, description="source bundle hash")

    @model_validator(mode="after")
    def validate_paths(self) -> "SourceBundleReference":
        if self.repository_relative_archive_path != FIXED_SOURCE_ARCHIVE_PATH:
            raise ValueError("source archive path is not canonical")
        if self.repository_relative_inventory_path != FIXED_SOURCE_INVENTORY_PATH:
            raise ValueError("source inventory path is not canonical")
        if tuple(entry.path for entry in self.files) != tuple(
            sorted(entry.path for entry in self.files)
        ):
            raise ValueError("source bundle file inventory must be sorted")
        return self


@dataclass(frozen=True, slots=True)
class BuiltSourceBundle:
    archive_path: Path
    inventory_path: Path
    reference: SourceBundleReference


def build_phase40_source_bundle(repo_root: Path, output_root: Path) -> BuiltSourceBundle:
    root = Path(repo_root).resolve(strict=True)
    output_root = Path(output_root)
    expected_output_root = Path(
        os.path.abspath(
            os.path.normpath(os.fspath(root / PurePosixPath(FIXED_SOURCE_ARCHIVE_PATH).parent))
        )
    )
    supplied_output_root = Path(
        os.path.abspath(os.path.normpath(os.fspath(output_root)))
    )
    if supplied_output_root != expected_output_root:
        raise ValueError("source bundle output root is not the canonical repository location")
    entries: list[SourceInventoryEntry] = []
    members: list[tuple[str, bytes]] = []
    allowlist = tuple(sorted(PHASE40_SOURCE_ALLOWLIST))
    if len(allowlist) != len(set(allowlist)):
        raise RuntimeError("Phase 40 source allowlist contains duplicates")
    for relative in allowlist:
        normalized = _safe_relative_path(relative, description="source allowlist path")
        path = root / PurePosixPath(normalized)
        if not path.exists() or not path.is_file():
            raise FileNotFoundError(f"missing allowlisted Phase 40 source: {normalized}")
        if _path_is_redirect(path):
            raise ValueError(f"allowlisted Phase 40 source is a symbolic link: {normalized}")
        if root not in path.resolve(strict=True).parents:
            raise ValueError(f"allowlisted Phase 40 source escapes repository: {normalized}")
        payload = path.read_bytes()
        entries.append(SourceInventoryEntry(path=normalized, bytes=len(payload), sha256=_sha256(payload)))
        members.append((normalized, payload))

    archive_bytes = _deterministic_zip(tuple(members))
    inventory = SourceInventory(
        archive_sha256=_sha256(archive_bytes),
        files=tuple(entries),
    )
    inventory_bytes = _canonical_json_bytes(inventory.model_dump(mode="json"))
    archive_path = _atomic_write_bytes(output_root / "phase40-source.zip", archive_bytes)
    inventory_path = _atomic_write_bytes(
        output_root / "phase40-source-manifest.json", inventory_bytes
    )
    reference = SourceBundleReference(
        archive_sha256=_sha256(archive_bytes),
        inventory_sha256=_sha256(inventory_bytes),
        files=inventory.files,
    )
    return BuiltSourceBundle(archive_path, inventory_path, reference)


def verify_phase40_source_bundle(
    *,
    repo_root: Path,
    reference: SourceBundleReference,
    archive_path: Path | None = None,
    inventory_path: Path | None = None,
) -> SourceInventory:
    root = Path(repo_root).resolve(strict=True)
    expected_archive = root / reference.repository_relative_archive_path
    expected_inventory = root / reference.repository_relative_inventory_path
    supplied_archive = Path(archive_path or expected_archive).resolve(strict=False)
    supplied_inventory = Path(inventory_path or expected_inventory).resolve(strict=False)
    if supplied_archive != expected_archive.resolve(strict=False):
        raise ValueError("source archive path is not request-bound")
    if supplied_inventory != expected_inventory.resolve(strict=False):
        raise ValueError("source inventory path is not request-bound")
    archive_bytes = supplied_archive.read_bytes()
    inventory_bytes = supplied_inventory.read_bytes()
    if _sha256(archive_bytes) != reference.archive_sha256:
        raise ValueError("source archive SHA-256 mismatch")
    if _sha256(inventory_bytes) != reference.inventory_sha256:
        raise ValueError("source inventory SHA-256 mismatch")
    inventory = SourceInventory.model_validate_json(inventory_bytes)
    if inventory.archive_sha256 != reference.archive_sha256:
        raise ValueError("source inventory archive identity differs from the request")
    if inventory.files != reference.files:
        raise ValueError("source inventory differs from the run request")
    expected_paths = tuple(sorted(PHASE40_SOURCE_ALLOWLIST))
    if tuple(entry.path for entry in inventory.files) != expected_paths:
        raise ValueError("source inventory is not the complete runtime allowlist")
    with zipfile.ZipFile(io.BytesIO(archive_bytes), "r") as archive:
        infos = archive.infolist()
        names = tuple(info.filename for info in infos)
        if names != tuple(entry.path for entry in inventory.files):
            raise ValueError("source archive file set/order differs from inventory")
        for info, entry in zip(infos, inventory.files, strict=True):
            _safe_archive_member(info.filename)
            if info.is_dir() or ((info.external_attr >> 16) & 0o170000) == stat.S_IFLNK:
                raise ValueError("source archive contains a directory or symbolic link")
            payload = archive.read(info.filename)
            if len(payload) != entry.bytes or _sha256(payload) != entry.sha256:
                raise ValueError(f"source archive member identity mismatch: {entry.path}")
    return inventory


class FullRunRequestIdentity(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    run_id: str
    model_family: ModelFamily
    adaptation_mode: AdaptationMode
    run_kind: Literal["full"] = "full"
    returned_root: str
    step_origin: Literal[0] = 0
    probe_parent: None = None

    @field_validator("run_id")
    @classmethod
    def validate_run_id(cls, value: str) -> str:
        if not _SAFE_RUN_ID_RE.fullmatch(value):
            raise ValueError("run_id must be a safe normalized identifier")
        return value

    @field_validator("returned_root")
    @classmethod
    def validate_root(cls, value: str) -> str:
        return _safe_relative_path(value, description="returned bundle root")


class RequestedControlTemplate(BaseModel):
    """Strict pre-run controls with runtime accelerator facts intentionally absent."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["phase40-requested-control-template-v1"] = (
        "phase40-requested-control-template-v1"
    )
    controls_without_accelerator: dict[str, Any]

    @model_validator(mode="after")
    def validate_complete_non_hardware_controls(self) -> "RequestedControlTemplate":
        controls = dict(self.controls_without_accelerator)
        if "accelerator" in controls:
            raise ValueError("run request must not contain guessed or returned accelerator facts")
        expected = set(ResumeControlledConfig.model_fields) - {"accelerator"}
        if set(controls) != expected:
            missing = sorted(expected - set(controls))
            extra = sorted(set(controls) - expected)
            raise ValueError(
                f"requested controls must be exact; missing={missing}, extra={extra}"
            )
        validated = self.materialize_for_validation()
        normalized = validated.model_dump(mode="json")
        normalized.pop("accelerator", None)
        object.__setattr__(self, "controls_without_accelerator", normalized)
        return self

    def materialize_for_validation(self) -> ResumeControlledConfig:
        payload = dict(self.controls_without_accelerator)
        payload["accelerator"] = AcceleratorIdentity(
            accelerator_type="operator-supplied",
            accelerator_name="operator-supplied",
            compute_capability=None,
            total_memory_bytes=0,
        ).model_dump(mode="json")
        return ResumeControlledConfig.model_validate_json(
            json.dumps(
                payload,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            )
        )

    @property
    def sha256(self) -> str:
        return _sha256(
            b"phase40-requested-control-template-v1\0"
            + _canonical_json_bytes(self.controls_without_accelerator)
        )

    def verify_runtime_config(self, config: ResumeControlledConfig) -> None:
        runtime_payload = config.model_dump(mode="json")
        runtime_payload.pop("accelerator", None)
        if runtime_payload != self.controls_without_accelerator:
            raise RuntimeError("returned controlled config differs from the frozen non-hardware controls")


class RunRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["phase40-full-run-request-v1"] = PHASE40_RUN_REQUEST_SCHEMA_VERSION
    runs: tuple[FullRunRequestIdentity, FullRunRequestIdentity, FullRunRequestIdentity]
    source_bundle: SourceBundleReference
    input_bundle: InputBundleReference
    package_candidates: tuple[str, str] = PACKAGE_CANDIDATES
    expected_bundle_files: tuple[str, ...]
    control_template_by_run: dict[str, RequestedControlTemplate]
    control_template_digest_by_run: dict[str, str]
    no_held_out_boundary: Literal[True] = True
    git_commit: str | None = None

    @field_validator("expected_bundle_files")
    @classmethod
    def validate_expected_files(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        normalized = tuple(_safe_relative_path(item, description="expected bundle file") for item in value)
        if normalized != REQUIRED_FULL_BUNDLE_FILES:
            raise ValueError("expected bundle files must equal the fixed complete-output contract")
        return normalized

    @field_validator("control_template_digest_by_run")
    @classmethod
    def validate_control_hashes(cls, value: dict[str, str]) -> dict[str, str]:
        for digest in value.values():
            _require_sha256(digest, description="control-template digest")
        return value

    @field_validator("git_commit")
    @classmethod
    def reject_blank_git(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("git_commit cannot be blank")
        return value

    @model_validator(mode="after")
    def validate_exact_runs(self) -> "RunRequest":
        expected = {
            (ModelFamily.QWEN, AdaptationMode.LORA),
            (ModelFamily.QWEN, AdaptationMode.QLORA),
            (ModelFamily.PHOBERT, AdaptationMode.CLASSIFICATION_HEAD),
        }
        actual = {(run.model_family, run.adaptation_mode) for run in self.runs}
        if actual != expected or len(actual) != 3:
            raise ValueError("run request requires exactly Qwen LoRA, Qwen QLoRA, and PhoBERT full")
        roots = tuple(run.returned_root for run in self.runs)
        if set(roots) != set(FIXED_RETURNED_ROOTS) or len(set(roots)) != 3:
            raise ValueError("run request returned roots are not the three canonical roots")
        expected_roots = {
            (ModelFamily.QWEN, AdaptationMode.LORA): FIXED_RETURNED_ROOTS[0],
            (ModelFamily.QWEN, AdaptationMode.QLORA): FIXED_RETURNED_ROOTS[1],
            (ModelFamily.PHOBERT, AdaptationMode.CLASSIFICATION_HEAD): FIXED_RETURNED_ROOTS[2],
        }
        for run in self.runs:
            if run.returned_root != expected_roots[(run.model_family, run.adaptation_mode)]:
                raise ValueError("run identity is mapped to the wrong canonical returned root")
        run_ids = {run.run_id for run in self.runs}
        if (
            len(run_ids) != 3
            or set(self.control_template_digest_by_run) != run_ids
            or set(self.control_template_by_run) != run_ids
        ):
            raise ValueError("control templates and digests must cover exactly the three run IDs")
        if self.package_candidates != PACKAGE_CANDIDATES:
            raise ValueError("run request package candidates differ from the fixed pins")
        run_by_id = {run.run_id: run for run in self.runs}
        validation_configs: dict[str, ResumeControlledConfig] = {}
        for run_id, template in self.control_template_by_run.items():
            config = template.materialize_for_validation()
            validation_configs[run_id] = config
            run = run_by_id[run_id]
            identity = config.experiment_identity
            if (
                identity.model_family != run.model_family
                or identity.adaptation_mode != run.adaptation_mode
                or identity.run_kind != RunKind.FULL
            ):
                raise ValueError("controlled config identity differs from its requested full run")
            pinned_revision = (
                PINNED_PHOBERT_REVISION
                if run.model_family == ModelFamily.PHOBERT
                else PINNED_QWEN_REVISION
            )
            pinned_model_id = (
                PINNED_PHOBERT_MODEL_ID
                if run.model_family == ModelFamily.PHOBERT
                else PINNED_QWEN_MODEL_ID
            )
            if config.model_id != pinned_model_id:
                raise ValueError("controlled config model ID is not the pinned Phase 40 model")
            if config.model_revision != pinned_revision:
                raise ValueError("controlled config model revision is not the pinned Phase 40 revision")
            if config.seed != 42 or config.data_seed != 42:
                raise ValueError("Phase 40 full runs require the predeclared seed/data_seed 42")
            for split, member in zip(config.splits, self.input_bundle.data_members, strict=True):
                if (
                    split.logical_name != member.logical_name
                    or split.records != member.records
                    or split.bytes != member.bytes
                    or split.sha256 != member.sha256
                    or split.ordered_row_ids_sha256 != member.ordered_row_ids_sha256
                ):
                    raise ValueError("controlled config split identity differs from the input bundle")
            if template.sha256 != self.control_template_digest_by_run[run_id]:
                raise ValueError("run request control-template digest does not match its controls")
        qwen_configs = {
            config.experiment_identity.adaptation_mode: config
            for config in validation_configs.values()
            if config.experiment_identity.model_family == ModelFamily.QWEN
        }
        if not compare_qwen_configs(
            qwen_configs[AdaptationMode.LORA], qwen_configs[AdaptationMode.QLORA]
        ).admissible:
            raise ValueError("requested Qwen controls differ beyond base-weight quantization")
        return self


def freeze_phase40_run_request(
    request: RunRequest,
    *,
    repo_root: Path,
    output_path: Path | None = None,
) -> Path:
    """Freeze and reverify the canonical external full-run request.

    The source and input authorities are verified before the first write.  A
    replay is accepted only when the existing request bytes are identical;
    changing source, data, controls, or identities therefore requires an
    explicitly new handoff rather than silently replacing operator authority.
    """

    root = Path(repo_root).resolve(strict=True)
    typed = request if isinstance(request, RunRequest) else RunRequest.model_validate(request)
    verify_phase40_run_request(typed, repo_root=root, verify_input=True)
    destination = Path(output_path or (root / FIXED_RUN_REQUEST_PATH))
    expected = Path(os.path.abspath(os.path.normpath(os.fspath(root / FIXED_RUN_REQUEST_PATH))))
    supplied = Path(os.path.abspath(os.path.normpath(os.fspath(destination))))
    if supplied != expected:
        raise ValueError("full-run request output path is not canonical")
    payload = _canonical_json_bytes(typed.model_dump(mode="json"))
    frozen = _write_frozen_bytes(supplied, payload)
    read_back = RunRequest.model_validate_json(
        frozen.read_text(encoding="utf-8", errors="strict")
    )
    if read_back != typed:
        raise RuntimeError("frozen full-run request changed during read-back")
    verify_phase40_run_request(read_back, repo_root=root, verify_input=True)
    return frozen


def load_frozen_phase40_run_request(
    *,
    repo_root: Path,
    request_path: Path | None = None,
) -> RunRequest:
    """Load the sole canonical request and reverify both transfer authorities."""

    root = _trusted_repo_root(repo_root)
    supplied = Path(request_path or (root / FIXED_RUN_REQUEST_PATH))
    expected = _lexical_absolute(root / FIXED_RUN_REQUEST_PATH)
    absolute = _lexical_absolute(supplied)
    _reject_redirecting_path_components((absolute,))
    if absolute != expected or not absolute.is_file() or absolute.is_symlink():
        raise ValueError("full-run request path is not the canonical regular file")
    payload = absolute.read_bytes()
    request = RunRequest.model_validate_json(payload)
    if payload != _canonical_json_bytes(request.model_dump(mode="json")):
        raise RuntimeError("frozen full-run request bytes are not canonical")
    return verify_phase40_run_request(request, repo_root=root, verify_input=True)


def require_canonical_phase40_run_request(
    request: RunRequest,
    *,
    repo_root: Path,
) -> RunRequest:
    """Reload canonical raw request bytes and require object equality."""

    supplied = request if isinstance(request, RunRequest) else RunRequest.model_validate(request)
    canonical = load_frozen_phase40_run_request(repo_root=repo_root)
    if supplied != canonical:
        raise ValueError("supplied run request differs from the canonical frozen request")
    return canonical


class ProbeArtifactIdentity(BaseModel):
    """One immutable file retained from the bounded local LoRA probe."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    relative_path: str
    bytes: int = Field(gt=0)
    sha256: str

    @field_validator("relative_path")
    @classmethod
    def validate_relative_path(cls, value: str) -> str:
        normalized = _safe_relative_path(value, description="LoRA probe artifact")
        if normalized not in FIXED_LORA_PROBE_FILES:
            raise ValueError("LoRA probe artifact is not in the fixed evidence set")
        return normalized

    @field_validator("sha256")
    @classmethod
    def validate_sha256(cls, value: str) -> str:
        return _require_sha256(value, description="LoRA probe artifact hash")


class LoraProbeAuthority(BaseModel):
    """Hash authority for resource evidence; it never authorizes predictions."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    root: str = FIXED_LORA_PROBE_ROOT
    artifacts: tuple[ProbeArtifactIdentity, ...]

    @model_validator(mode="after")
    def validate_exact_artifacts(self) -> "LoraProbeAuthority":
        if self.root != FIXED_LORA_PROBE_ROOT:
            raise ValueError("LoRA probe root is not the fixed local evidence root")
        paths = tuple(artifact.relative_path for artifact in self.artifacts)
        if paths != FIXED_LORA_PROBE_FILES:
            raise ValueError("LoRA probe authority must bind the exact ordered evidence set")
        return self

    @property
    def sha256(self) -> str:
        return _sha256(
            b"phase40-lora-probe-authority-v1\0"
            + _canonical_json_bytes(self.model_dump(mode="json"))
        )


def _module_name_from_relative_path(relative_path: str) -> str:
    path = PurePosixPath(relative_path)
    parts = list(path.with_suffix("").parts)
    if parts[-1] == "__init__":
        parts.pop()
    return ".".join(parts)


def _comparison_finalizer_import_closure(repo_root: Path) -> tuple[str, ...]:
    """Statically close all local Python imports of the comparison CLI."""

    root = _trusted_repo_root(repo_root)
    _reject_redirecting_path_components(
        tuple(root / path for path in PHASE40_COMPARISON_FINALIZER_SOURCE_ALLOWLIST)
    )
    module_paths: dict[str, tuple[str, Path]] = {}
    for relative in PHASE40_COMPARISON_FINALIZER_SOURCE_ALLOWLIST:
        if relative.endswith(".py"):
            module_paths[_module_name_from_relative_path(relative)] = (
                relative,
                root / relative,
            )

    queue = [
        _module_name_from_relative_path(path)
        for path in PHASE40_COMPARISON_FINALIZER_ENTRYPOINTS
    ]
    visited: set[str] = set()
    relative_paths: set[str] = set()

    def enqueue(module_name: str, *, required: bool = True) -> None:
        if not module_name.startswith("src"):
            return
        if module_name not in module_paths:
            if required:
                raise ValueError(
                    f"comparison finalizer imports an unbound local module: {module_name}"
                )
            return
        queue.append(module_name)

    while queue:
        module_name = queue.pop()
        if module_name in visited:
            continue
        if module_name not in module_paths:
            raise ValueError(f"comparison finalizer local import is missing: {module_name}")
        visited.add(module_name)
        relative, path = module_paths[module_name]
        relative_paths.add(relative)
        module_parts = module_name.split(".")
        for index in range(1, len(module_parts)):
            enqueue(".".join(module_parts[:index]))
        try:
            tree = ast.parse(path.read_text(encoding="utf-8", errors="strict"))
        except (SyntaxError, UnicodeDecodeError) as exc:
            raise ValueError(f"comparison finalizer source is not parseable: {relative}") from exc
        current_is_package = PurePosixPath(relative).name == "__init__.py"
        current_package = module_parts if current_is_package else module_parts[:-1]
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    enqueue(alias.name)
            elif isinstance(node, ast.ImportFrom):
                if node.level:
                    keep = len(current_package) - (node.level - 1)
                    if keep < 0:
                        raise ValueError(f"invalid relative import in {relative}")
                    base_parts = current_package[:keep]
                    if node.module:
                        base_parts += node.module.split(".")
                    base = ".".join(base_parts)
                else:
                    base = node.module or ""
                enqueue(base)
                for alias in node.names:
                    if alias.name != "*":
                        enqueue(
                            f"{base}.{alias.name}" if base else alias.name,
                            required=False,
                        )
            elif (
                isinstance(node, ast.Call)
                and node.args
                and isinstance(node.args[0], ast.Constant)
                and isinstance(node.args[0].value, str)
                and node.args[0].value.startswith("src.")
            ):
                function = node.func
                if (
                    isinstance(function, ast.Name)
                    and function.id == "__import__"
                ) or (
                    isinstance(function, ast.Attribute)
                    and function.attr == "import_module"
                ):
                    enqueue(node.args[0].value)
    return tuple(sorted(relative_paths))


def _assert_comparison_finalizer_import_closed(repo_root: Path) -> None:
    expected = {
        path
        for path in PHASE40_COMPARISON_FINALIZER_SOURCE_ALLOWLIST
        if path.endswith(".py")
    }
    actual = set(_comparison_finalizer_import_closure(repo_root))
    if actual != expected:
        raise ValueError(
            "comparison finalizer authority is not import-closed; "
            f"missing={sorted(actual - expected)}, extra={sorted(expected - actual)}"
        )


class ComparisonFinalizerAuthority(BaseModel):
    """Separate live-source pin for code absent from training source-runtime-v3."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["phase40-comparison-finalizer-authority-v1"] = (
        "phase40-comparison-finalizer-authority-v1"
    )
    runtime_origin: Literal["local_hash_pinned_source_not_training_runtime_v3"] = (
        "local_hash_pinned_source_not_training_runtime_v3"
    )
    files: tuple[SourceInventoryEntry, ...]
    source_tree_sha256: str

    @field_validator("source_tree_sha256")
    @classmethod
    def validate_tree_hash(cls, value: str) -> str:
        return _require_sha256(value, description="comparison finalizer source-tree hash")

    @model_validator(mode="after")
    def validate_file_set(self) -> "ComparisonFinalizerAuthority":
        paths = tuple(file.path for file in self.files)
        if paths != PHASE40_COMPARISON_FINALIZER_SOURCE_ALLOWLIST:
            raise ValueError("comparison finalizer authority must bind the exact source allowlist")
        expected = _sha256(
            b"phase40-comparison-finalizer-source-v1\0"
            + _canonical_json_bytes([file.model_dump(mode="json") for file in self.files])
        )
        if self.source_tree_sha256 != expected:
            raise ValueError("comparison finalizer source-tree hash differs from its inventory")
        return self


def _build_comparison_finalizer_authority(repo_root: Path) -> ComparisonFinalizerAuthority:
    root = _trusted_repo_root(repo_root)
    source_paths = tuple(root / relative for relative in PHASE40_COMPARISON_FINALIZER_SOURCE_ALLOWLIST)
    _reject_redirecting_path_components(source_paths)
    _assert_comparison_finalizer_import_closed(root)
    entries: list[SourceInventoryEntry] = []
    for relative_path, path in zip(
        PHASE40_COMPARISON_FINALIZER_SOURCE_ALLOWLIST,
        source_paths,
        strict=True,
    ):
        if not path.is_file() or path.is_symlink():
            raise ValueError(f"comparison finalizer source is missing or unsafe: {relative_path}")
        payload = path.read_bytes()
        entries.append(
            SourceInventoryEntry(
                path=relative_path,
                bytes=len(payload),
                sha256=_sha256(payload),
            )
        )
    files = tuple(entries)
    return ComparisonFinalizerAuthority(
        files=files,
        source_tree_sha256=_sha256(
            b"phase40-comparison-finalizer-source-v1\0"
            + _canonical_json_bytes([file.model_dump(mode="json") for file in files])
        ),
    )


def _verify_comparison_finalizer_authority(
    authority: ComparisonFinalizerAuthority,
    *,
    repo_root: Path,
) -> None:
    actual = _build_comparison_finalizer_authority(repo_root)
    if actual != authority:
        raise ValueError("local comparison finalizer source differs from the scope amendment")


class Phase40ScopeAmendment(BaseModel):
    """Additive waiver that leaves the frozen three-run request byte-identical."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["phase40-two-full-model-scope-amendment-v1"] = (
        PHASE40_SCOPE_AMENDMENT_SCHEMA_VERSION
    )
    original_run_request_path: Literal["data/models/phase40/full-run-request.json"] = (
        FIXED_RUN_REQUEST_PATH
    )
    original_run_request_sha256: str
    active_full_run_ids: tuple[str, str]
    active_returned_roots: tuple[str, str] = FIXED_ACTIVE_RETURNED_ROOTS
    waived_full_run_id: str
    waived_returned_root: Literal["data/models/phase40/full/qwen-lora"] = (
        FIXED_RETURNED_ROOTS[0]
    )
    full_lora_disposition: Literal["cancelled_before_start"] = "cancelled_before_start"
    waiver_action: Literal["withdrawn"] = "withdrawn"
    waiver_basis: Literal[
        "bounded_local_probe_established_resource_pressure_and_deadline_mismatch"
    ] = "bounded_local_probe_established_resource_pressure_and_deadline_mismatch"
    lora_probe_authority: LoraProbeAuthority
    comparison_finalizer_authority: ComparisonFinalizerAuthority
    quality_model_run_ids: tuple[str, str]
    review_model_run_ids: tuple[str, str]
    execution_policy: Literal["local_primary"] = "local_primary"
    colab_contingency_policy: Literal[
        "validation_only_before_held_out_open_if_local_quality_unacceptable"
    ] = "validation_only_before_held_out_open_if_local_quality_unacceptable"
    no_held_out_boundary: Literal[True] = True

    @field_validator("original_run_request_sha256")
    @classmethod
    def validate_request_hash(cls, value: str) -> str:
        return _require_sha256(value, description="original run-request hash")

    @field_validator("active_full_run_ids", "quality_model_run_ids", "review_model_run_ids")
    @classmethod
    def validate_run_ids(cls, value: tuple[str, str]) -> tuple[str, str]:
        if len(set(value)) != 2 or any(not _SAFE_RUN_ID_RE.fullmatch(item) for item in value):
            raise ValueError("two-model run IDs must be unique safe identifiers")
        return value

    @field_validator("waived_full_run_id")
    @classmethod
    def validate_waived_run_id(cls, value: str) -> str:
        if not _SAFE_RUN_ID_RE.fullmatch(value):
            raise ValueError("waived run ID must be a safe identifier")
        return value

    @model_validator(mode="after")
    def validate_scope_policy(self) -> "Phase40ScopeAmendment":
        if self.active_returned_roots != FIXED_ACTIVE_RETURNED_ROOTS:
            raise ValueError("scope amendment must retain exactly QLoRA and PhoBERT roots")
        if self.quality_model_run_ids != self.active_full_run_ids:
            raise ValueError("quality comparison must contain exactly the two active full runs")
        if self.review_model_run_ids != self.active_full_run_ids:
            raise ValueError("human review must contain exactly the two active full runs")
        if self.waived_full_run_id in self.active_full_run_ids:
            raise ValueError("waived full LoRA run cannot appear in the active model set")
        return self

    @property
    def sha256(self) -> str:
        return _sha256(
            b"phase40-two-full-model-scope-amendment-v1\0"
            + _canonical_json_bytes(self.model_dump(mode="json"))
        )


class LoraProbeComparisonRecord(BaseModel):
    """Mechanical resource-only summary derived from the sealed probe files."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    run_id: str
    run_kind: Literal["probe"] = "probe"
    adaptation_mode: Literal["lora"] = "lora"
    full_run_disposition: Literal["cancelled_before_start"] = "cancelled_before_start"
    evidence_authority_sha256: str
    observed_optimizer_steps: int = Field(gt=0)
    retained_optimizer_steps: int = Field(gt=0)
    steady_state_step_seconds_median: float = Field(gt=0)
    peak_device_vram_used_mib: float = Field(gt=0)
    minimum_device_vram_free_mib: float = Field(ge=0)
    peak_system_ram_used_bytes: float = Field(gt=0)
    memory_constrained: Literal[True] = True
    oom_observed: Literal[False] = False
    feasibility_claim: Literal[
        "technically_runnable_but_operationally_impractical_under_deadline"
    ] = "technically_runnable_but_operationally_impractical_under_deadline"
    discarded_runtime_path_absent: Literal[True] = True
    comparison_eligible: Literal[False] = False
    predictions_included: Literal[False] = False

    @field_validator("evidence_authority_sha256")
    @classmethod
    def validate_authority_hash(cls, value: str) -> str:
        return _require_sha256(value, description="LoRA probe authority hash")

    @model_validator(mode="after")
    def validate_probe_bounds(self) -> "LoraProbeComparisonRecord":
        if self.retained_optimizer_steps > self.observed_optimizer_steps:
            raise ValueError("retained LoRA probe steps cannot exceed observed steps")
        return self


def _regular_probe_artifact(root: Path, artifact: ProbeArtifactIdentity) -> Path:
    path = root / artifact.relative_path
    if not path.is_file() or path.is_symlink():
        raise ValueError(f"LoRA probe artifact is missing or unsafe: {artifact.relative_path}")
    payload = path.read_bytes()
    if len(payload) != artifact.bytes or _sha256(payload) != artifact.sha256:
        raise ValueError(f"LoRA probe artifact identity mismatch: {artifact.relative_path}")
    return path


def verify_lora_probe_authority(
    authority: LoraProbeAuthority,
    *,
    repo_root: Path,
) -> LoraProbeComparisonRecord:
    """Verify the sealed bounded probe and derive resource claims without predictions."""

    authority = (
        authority
        if isinstance(authority, LoraProbeAuthority)
        else LoraProbeAuthority.model_validate(authority)
    )
    repository = _trusted_repo_root(repo_root)
    root = repository / authority.root
    artifact_paths = tuple(root / artifact.relative_path for artifact in authority.artifacts)
    _reject_redirecting_path_components((root, *artifact_paths))
    if not root.is_dir() or root.is_symlink():
        raise ValueError("fixed LoRA probe evidence root is missing or unsafe")
    paths = {
        artifact.relative_path: _regular_probe_artifact(root, artifact)
        for artifact in authority.artifacts
    }
    try:
        outcome = json.loads(paths["outcome.json"].read_text(encoding="utf-8", errors="strict"))
        discard = json.loads(
            paths["discard-receipt.json"].read_text(encoding="utf-8", errors="strict")
        )
        proof = QuantizationProofEvidence.model_validate_json(
            paths["quantization-proof.json"].read_text(encoding="utf-8", errors="strict")
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("LoRA probe JSON evidence is invalid") from exc
    if not isinstance(outcome, dict) or not isinstance(discard, dict):
        raise ValueError("LoRA probe outcome/discard evidence must be JSON objects")
    if (
        proof.requested_mode != AdaptationMode.LORA
        or proof.resolved_mode != ResolvedQwenMode.FULL_PRECISION_LORA
        or proof.load_in_4bit
        or proof.bitsandbytes_version is not None
    ):
        raise ValueError("LoRA probe quantization proof is not full-precision LoRA")
    artifacts_by_name = {artifact.relative_path: artifact for artifact in authority.artifacts}
    expected_outcome_refs = {
        "telemetry.jsonl": ("telemetry", "telemetry_sha256"),
        "optimizer-events.jsonl": ("optimizer_events", "optimizer_events_sha256"),
        "quantization-proof.json": ("quantization_proof", "quantization_proof_sha256"),
    }
    for name, (path_key, hash_key) in expected_outcome_refs.items():
        if (
            outcome.get(path_key) != f"lora-retry-1/{name}"
            or outcome.get(hash_key) != artifacts_by_name[name].sha256
        ):
            raise ValueError(f"LoRA probe outcome does not bind {name}")
    embedded_discard = outcome.get("discard_receipt")
    if embedded_discard != discard:
        raise ValueError("LoRA probe outcome and discard receipt differ")
    if (
        discard.get("schema_version") != "phase40-discard-v1"
        or discard.get("run_id") != "rtx5050-lora-retry-1"
        or discard.get("path_absent") is not True
        or discard.get("removal_result") != "removed"
    ):
        raise ValueError("LoRA probe runtime was not verifiably discarded")
    if (
        outcome.get("schema_version") != "phase40-local-outcome-v1"
        or outcome.get("status") != "error"
        or outcome.get("stop_reason") != "parent_controller_error"
        or outcome.get("measured_target_reached") is not False
        or outcome.get("losses_finite") is not True
    ):
        raise ValueError("LoRA probe outcome is not the bounded retained evidence contract")
    memory = outcome.get("memory_pressure")
    peaks = outcome.get("resource_peaks")
    if (
        not isinstance(memory, dict)
        or memory.get("memory_constrained") is not True
        or memory.get("classification") != "gpu_pressure"
        or memory.get("oom_kind") is not None
        or not isinstance(peaks, dict)
    ):
        raise ValueError("LoRA probe does not establish the required resource constraint")
    for name in ("telemetry.jsonl", "optimizer-events.jsonl"):
        payload = paths[name].read_text(encoding="utf-8", errors="strict")
        if not payload.endswith("\n") or any(not line for line in payload.splitlines()):
            raise ValueError(f"LoRA probe {name} is not complete JSONL")
        try:
            if any(not isinstance(json.loads(line), dict) for line in payload.splitlines()):
                raise ValueError(f"LoRA probe {name} contains a non-object row")
        except json.JSONDecodeError as exc:
            raise ValueError(f"LoRA probe {name} is invalid JSONL") from exc
    try:
        record = LoraProbeComparisonRecord(
            run_id=discard["run_id"],
            evidence_authority_sha256=authority.sha256,
            observed_optimizer_steps=outcome["observed_optimizer_steps"],
            retained_optimizer_steps=outcome["retained_optimizer_steps"],
            steady_state_step_seconds_median=outcome["steady_state_step_seconds_median"],
            peak_device_vram_used_mib=memory["peak_device_vram_used_mib"],
            minimum_device_vram_free_mib=memory["minimum_device_vram_free_mib"],
            peak_system_ram_used_bytes=peaks["system_ram_used_bytes"],
            memory_constrained=True,
            oom_observed=False,
            discarded_runtime_path_absent=True,
            comparison_eligible=False,
            predictions_included=False,
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError("LoRA probe resource summary is incomplete or invalid") from exc
    if record.observed_optimizer_steps >= 1245:
        raise ValueError("LoRA resource evidence is not a bounded probe")
    return record


def build_phase40_scope_amendment(
    request: RunRequest,
    *,
    repo_root: Path,
) -> Phase40ScopeAmendment:
    """Build the additive two-full-model waiver from fixed local evidence."""

    request = request if isinstance(request, RunRequest) else RunRequest.model_validate(request)
    verify_phase40_run_request(request, repo_root=repo_root, verify_input=True)
    repository = _trusted_repo_root(repo_root)
    probe_root = repository / FIXED_LORA_PROBE_ROOT
    probe_paths = tuple(probe_root / name for name in FIXED_LORA_PROBE_FILES)
    _reject_redirecting_path_components((probe_root, *probe_paths))
    if any(not path.is_file() or path.is_symlink() for path in probe_paths):
        raise ValueError("fixed LoRA probe evidence set is missing or unsafe")
    artifacts = tuple(
        ProbeArtifactIdentity(
            relative_path=name,
            bytes=path.stat().st_size,
            sha256=_sha256(path.read_bytes()),
        )
        for name, path in zip(FIXED_LORA_PROBE_FILES, probe_paths, strict=True)
    )
    probe_authority = LoraProbeAuthority(artifacts=artifacts)
    verify_lora_probe_authority(probe_authority, repo_root=repo_root)
    by_mode = {
        (run.model_family, run.adaptation_mode): run for run in request.runs
    }
    lora = by_mode[(ModelFamily.QWEN, AdaptationMode.LORA)]
    qlora = by_mode[(ModelFamily.QWEN, AdaptationMode.QLORA)]
    phobert = by_mode[(ModelFamily.PHOBERT, AdaptationMode.CLASSIFICATION_HEAD)]
    active_ids = (qlora.run_id, phobert.run_id)
    return Phase40ScopeAmendment(
        original_run_request_sha256=_sha256(
            _canonical_json_bytes(request.model_dump(mode="json"))
        ),
        active_full_run_ids=active_ids,
        active_returned_roots=(qlora.returned_root, phobert.returned_root),
        waived_full_run_id=lora.run_id,
        waived_returned_root=lora.returned_root,
        lora_probe_authority=probe_authority,
        comparison_finalizer_authority=_build_comparison_finalizer_authority(repo_root),
        quality_model_run_ids=active_ids,
        review_model_run_ids=active_ids,
    )


def verify_phase40_scope_amendment(
    amendment: Phase40ScopeAmendment,
    *,
    request: RunRequest,
    repo_root: Path,
) -> LoraProbeComparisonRecord:
    amendment = (
        amendment
        if isinstance(amendment, Phase40ScopeAmendment)
        else Phase40ScopeAmendment.model_validate(amendment)
    )
    request = request if isinstance(request, RunRequest) else RunRequest.model_validate(request)
    expected_request_sha = _sha256(_canonical_json_bytes(request.model_dump(mode="json")))
    if amendment.original_run_request_sha256 != expected_request_sha:
        raise ValueError("scope amendment is bound to a different frozen run request")
    by_mode = {
        (run.model_family, run.adaptation_mode): run for run in request.runs
    }
    lora = by_mode[(ModelFamily.QWEN, AdaptationMode.LORA)]
    qlora = by_mode[(ModelFamily.QWEN, AdaptationMode.QLORA)]
    phobert = by_mode[(ModelFamily.PHOBERT, AdaptationMode.CLASSIFICATION_HEAD)]
    active = (qlora, phobert)
    if amendment.active_full_run_ids != tuple(run.run_id for run in active):
        raise ValueError("scope amendment active run IDs differ from QLoRA and PhoBERT")
    if amendment.active_returned_roots != tuple(run.returned_root for run in active):
        raise ValueError("scope amendment active roots differ from the frozen request")
    if (
        amendment.waived_full_run_id != lora.run_id
        or amendment.waived_returned_root != lora.returned_root
    ):
        raise ValueError("scope amendment does not waive exactly the frozen full LoRA run")
    _verify_comparison_finalizer_authority(
        amendment.comparison_finalizer_authority,
        repo_root=repo_root,
    )
    return verify_lora_probe_authority(
        amendment.lora_probe_authority,
        repo_root=repo_root,
    )


def freeze_phase40_scope_amendment(
    request: RunRequest,
    *,
    repo_root: Path,
    output_path: Path | None = None,
) -> Path:
    root = _trusted_repo_root(repo_root)
    frozen_request = load_frozen_phase40_run_request(repo_root=root)
    request = request if isinstance(request, RunRequest) else RunRequest.model_validate(request)
    if request != frozen_request:
        raise ValueError("scope amendment request differs from the canonical frozen request")
    amendment = build_phase40_scope_amendment(request, repo_root=root)
    destination = Path(output_path or (root / FIXED_SCOPE_AMENDMENT_PATH))
    expected = Path(os.path.abspath(os.path.normpath(os.fspath(root / FIXED_SCOPE_AMENDMENT_PATH))))
    supplied = Path(os.path.abspath(os.path.normpath(os.fspath(destination))))
    if supplied != expected:
        raise ValueError("scope amendment output path is not canonical")
    _reject_redirecting_path_components(
        (supplied,) if supplied.exists() else (supplied.parent,)
    )
    payload = _canonical_json_bytes(amendment.model_dump(mode="json"))
    path = _write_frozen_bytes(supplied, payload)
    loaded = Phase40ScopeAmendment.model_validate_json(path.read_bytes())
    verify_phase40_scope_amendment(loaded, request=request, repo_root=root)
    return path


def load_frozen_phase40_scope_amendment(
    *,
    request: RunRequest,
    repo_root: Path,
    amendment_path: Path | None = None,
) -> Phase40ScopeAmendment:
    root = _trusted_repo_root(repo_root)
    supplied = Path(amendment_path or (root / FIXED_SCOPE_AMENDMENT_PATH))
    expected = Path(os.path.abspath(os.path.normpath(os.fspath(root / FIXED_SCOPE_AMENDMENT_PATH))))
    absolute = Path(os.path.abspath(os.path.normpath(os.fspath(supplied))))
    _reject_redirecting_path_components((absolute,))
    if absolute != expected or not absolute.is_file() or absolute.is_symlink():
        raise ValueError("scope amendment path is not the canonical regular file")
    payload = absolute.read_bytes()
    amendment = Phase40ScopeAmendment.model_validate_json(payload)
    if payload != _canonical_json_bytes(amendment.model_dump(mode="json")):
        raise ValueError("scope amendment bytes are not canonical")
    verify_phase40_scope_amendment(amendment, request=request, repo_root=root)
    return amendment


def transfer_authority_from_request(request: RunRequest) -> TransferAuthorityEvidence:
    """Derive the exact evidence record from a validated, hardware-free request."""

    request = request if isinstance(request, RunRequest) else RunRequest.model_validate(request)
    return TransferAuthorityEvidence(
        schema_version="phase40-transfer-authority-v1",
        source_archive_sha256=request.source_bundle.archive_sha256,
        source_inventory_sha256=request.source_bundle.inventory_sha256,
        input_archive_sha256=request.input_bundle.archive_sha256,
        input_manifest_sha256=request.input_bundle.manifest_sha256,
        source_repository_relative_archive_path=(
            request.source_bundle.repository_relative_archive_path
        ),
        source_repository_relative_inventory_path=(
            request.source_bundle.repository_relative_inventory_path
        ),
        input_repository_relative_path=request.input_bundle.repository_relative_path,
        input_drive_path=request.input_bundle.drive_path,
        input_extraction_root=request.input_bundle.extraction_root,
        input_members=request.input_bundle.members,
        no_held_out_boundary=request.no_held_out_boundary,
    )


class PackageDecision(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    package: Literal["bitsandbytes==0.50.1", "matplotlib==3.11.1"]
    decision: Literal["approve", "reject"]
    reason: str | None = None

    @field_validator("reason")
    @classmethod
    def sanitize_reason(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = " ".join(value.split())
        if not stripped or len(stripped) > 300 or _SECRET_RE.search(stripped):
            raise ValueError("package reason must be short, non-secret text")
        if _WINDOWS_ABSOLUTE_RE.search(stripped) or "/Users/" in stripped or "\\Users\\" in stripped:
            raise ValueError("package reason cannot contain a personal absolute path")
        return stripped

    @model_validator(mode="after")
    def validate_reason_policy(self) -> "PackageDecision":
        if self.decision == "reject" and self.reason is None:
            raise ValueError("a rejected package requires a reason")
        return self


class ReturnedBundleRoot(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    run_id: str
    path: str

    @field_validator("path")
    @classmethod
    def validate_path(cls, value: str) -> str:
        normalized = _safe_relative_path(value, description="returned root")
        if normalized not in FIXED_RETURNED_ROOTS:
            raise ValueError("returned root is not canonical")
        return normalized


class ReturnedGpuIdentity(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    run_id: str
    accelerator: str = Field(min_length=1, max_length=160)

    @field_validator("accelerator")
    @classmethod
    def sanitize_accelerator(cls, value: str) -> str:
        stripped = " ".join(value.split())
        if _SECRET_RE.search(stripped) or _WINDOWS_ABSOLUTE_RE.search(stripped):
            raise ValueError("GPU identity contains secret or personal-path material")
        return stripped


class LocalTwoModelOperatorReturn(BaseModel):
    """Local-primary QLoRA/PhoBERT roots plus optional legacy package provenance."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    package_decisions: tuple[PackageDecision, ...] = ()
    bundle_roots: tuple[ReturnedBundleRoot, ...] = ()
    gpu_identities: tuple[ReturnedGpuIdentity, ...] = ()

    @model_validator(mode="after")
    def validate_return(self) -> "LocalTwoModelOperatorReturn":
        if self.package_decisions and tuple(
            decision.package for decision in self.package_decisions
        ) != PACKAGE_CANDIDATES:
            raise ValueError(
                "legacy package provenance, when supplied, must contain both fixed pins in order"
            )
        if (
            len(self.bundle_roots) != 2
            or tuple(root.path for root in self.bundle_roots) != FIXED_ACTIVE_RETURNED_ROOTS
        ):
            raise ValueError(
                "local operator return requires exactly QLoRA and PhoBERT bundle roots"
            )
        root_ids = {root.run_id for root in self.bundle_roots}
        gpu_ids = {gpu.run_id for gpu in self.gpu_identities}
        if len(self.gpu_identities) != 2 or root_ids != gpu_ids or len(root_ids) != 2:
            raise ValueError("local operator return requires one GPU identity per returned run")
        return self


# Deprecated import compatibility.  The object no longer represents a Colab
# approval gate; local run evidence is authoritative for runtime packages.
ColabOperatorReturn = LocalTwoModelOperatorReturn


class ComparisonRunRecord(BaseModel):
    """One re-verified full-run row retained in the comparison manifest."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    run_id: str
    model_family: ModelFamily
    adaptation_mode: AdaptationMode
    returned_root: str
    evidence_sha256: str
    resume_digest: str
    selected_checkpoint_identity: str
    selected_optimizer_step: int = Field(ge=0)
    safety_gate_passed: bool
    comparison_eligible: bool
    validation_rows: int = Field(gt=0)
    validation_metrics: dict[str, float]
    macro_f1: float = Field(ge=0, le=1)
    invalid_output_count: int = Field(ge=0)
    risky_recall_by_label: dict[str, float]
    gpu_identity: str
    package_versions: dict[str, str]
    required_tool_pins: dict[str, str]

    @field_validator("evidence_sha256", "resume_digest")
    @classmethod
    def validate_hashes(cls, value: str) -> str:
        return _require_sha256(value, description="comparison run hash")

    @field_validator("risky_recall_by_label")
    @classmethod
    def validate_risky_recall(cls, value: dict[str, float]) -> dict[str, float]:
        if set(value) != set(RISKY_RECALL_FLOORS):
            raise ValueError("risky recall must contain the three locked risky labels")
        if any(not 0 <= metric <= 1 for metric in value.values()):
            raise ValueError("risky recall values must be probabilities")
        return {label: value[label] for label in RISKY_RECALL_FLOORS}

    @field_validator("package_versions", "required_tool_pins")
    @classmethod
    def validate_runtime_packages(cls, value: dict[str, str]) -> dict[str, str]:
        if not value or any(not key or not version for key, version in value.items()):
            raise ValueError("runtime package/tool identities cannot be empty")
        return dict(sorted(value.items()))


class Phase40ComparisonManifest(BaseModel):
    """Machine-readable outcome of the amended two-full-model verification."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["phase40-comparison-v2"] = PHASE40_COMPARISON_SCHEMA_VERSION
    status: Literal["complete", "prestart_failed"]
    package_decisions: tuple[PackageDecision, ...] = ()
    original_run_request_sha256: str
    scope_amendment_sha256: str
    comparison_finalizer_source_sha256: str
    execution_policy: Literal["local_primary"] = "local_primary"
    full_lora_disposition: Literal["cancelled_before_start"] = "cancelled_before_start"
    lora_probe: LoraProbeComparisonRecord
    source_archive_sha256: str
    source_inventory_sha256: str
    input_archive_sha256: str
    input_manifest_sha256: str
    validation_rows: int = Field(gt=0)
    runs: tuple[ComparisonRunRecord, ...]
    qwen_config_comparison: QwenConfigComparison | None = None
    quality_comparison_admissible: bool
    hardware_confounded: bool | None
    speed_comparison_admissible: bool
    review_queue_rows: int = Field(ge=0)
    review_queue_sha256: str | None
    selected_prediction_bundles_sha256: str | None
    limitations: tuple[str, ...]
    failure_reason: str | None

    @field_validator(
        "source_archive_sha256",
        "source_inventory_sha256",
        "input_archive_sha256",
        "input_manifest_sha256",
        "original_run_request_sha256",
        "scope_amendment_sha256",
        "comparison_finalizer_source_sha256",
    )
    @classmethod
    def validate_authority_hashes(cls, value: str) -> str:
        return _require_sha256(value, description="comparison authority hash")

    @field_validator("review_queue_sha256", "selected_prediction_bundles_sha256")
    @classmethod
    def validate_optional_queue_hash(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return _require_sha256(value, description="review queue hash")

    @model_validator(mode="after")
    def validate_status_contract(self) -> "Phase40ComparisonManifest":
        single_seed = "single_training_seed_42_no_variance_or_significance_claim"
        if single_seed not in self.limitations:
            raise ValueError("comparison manifest must expose the single-seed limitation")
        if self.status == "prestart_failed":
            if self.runs or self.qwen_config_comparison is not None:
                raise ValueError("pre-start failure cannot contain model comparison results")
            if self.quality_comparison_admissible or self.speed_comparison_admissible:
                raise ValueError("pre-start failure cannot claim an admissible comparison")
            if (
                self.review_queue_rows
                or self.review_queue_sha256 is not None
                or self.selected_prediction_bundles_sha256 is not None
            ):
                raise ValueError("pre-start failure cannot claim a review queue")
            if self.failure_reason is None:
                raise ValueError("pre-start failure requires an explicit reason")
            return self
        if len(self.runs) != 2 or self.qwen_config_comparison is not None:
            raise ValueError("complete comparison requires exactly QLoRA and PhoBERT full runs")
        expected_models = (
            (ModelFamily.QWEN, AdaptationMode.QLORA),
            (ModelFamily.PHOBERT, AdaptationMode.CLASSIFICATION_HEAD),
        )
        if tuple((run.model_family, run.adaptation_mode) for run in self.runs) != expected_models:
            raise ValueError("complete comparison run order must be QLoRA then PhoBERT")
        if self.failure_reason is not None:
            raise ValueError("complete comparison cannot contain a failure reason")
        if (
            self.review_queue_rows <= 0
            or self.review_queue_sha256 is None
            or self.selected_prediction_bundles_sha256 is None
        ):
            raise ValueError("complete comparison requires the deterministic review queue")
        expected_quality = all(
            run.comparison_eligible and run.safety_gate_passed for run in self.runs
        )
        if self.quality_comparison_admissible != expected_quality:
            raise ValueError("quality admissibility differs from config and run safety evidence")
        if self.hardware_confounded is None:
            raise ValueError("complete comparison must state active-run hardware confounding")
        if self.speed_comparison_admissible:
            raise ValueError("probe-versus-full or cross-architecture speed claims are inadmissible")
        return self


@dataclass(frozen=True, slots=True)
class ComparisonArtifacts:
    manifest_path: Path
    report_path: Path
    review_queue_path: Path | None
    review_queue_manifest_path: Path | None
    reviewer_template_path: Path | None
    selected_prediction_bundles_path: Path | None
    manifest: Phase40ComparisonManifest
    prediction_bundles: tuple["SelectedPredictionBundle", ...]


def _read_json_or_jsonl(path: Path, *, description: str) -> object:
    if not path.is_file() or path.stat().st_size == 0:
        raise RuntimeError(f"{description} is missing or empty")
    try:
        text = path.read_text(encoding="utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise RuntimeError(f"{description} is not strict UTF-8") from exc
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        lines = text.splitlines()
        if not lines or any(not line for line in lines):
            raise RuntimeError(f"{description} JSONL contains an empty record")
        try:
            payload = [json.loads(line) for line in lines]
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"{description} is not valid JSON or JSONL") from exc
    if not isinstance(payload, (dict, list)) or not payload:
        raise RuntimeError(f"{description} is structurally empty")
    return payload


def _exact_artifact_for_role(evidence: RunEvidence, role: str):
    matches = tuple(artifact for artifact in evidence.artifacts if artifact.role == role)
    if len(matches) != 1:
        raise RuntimeError(f"run {evidence.run_id} requires exactly one {role} artifact")
    return matches[0]


def _artifact_for_sha(evidence: RunEvidence, role: str, sha256: str):
    matches = tuple(
        artifact
        for artifact in evidence.artifacts
        if artifact.role == role and artifact.sha256 == sha256
    )
    if len(matches) != 1:
        raise RuntimeError(
            f"run {evidence.run_id} selected checkpoint does not bind exactly one {role} artifact"
        )
    return matches[0]


def _prediction_row_from_payload(
    payload: Mapping[str, Any],
    *,
    model_family: ModelFamily,
) -> Phase40PredictionRow:
    try:
        validation_row_id = payload["validation_row_id"]
        sequence_index = payload.get("sequence_index", payload.get("canonical_index"))
        gold_label = payload["gold_label"]
        artifact_identity = payload["artifact_identity"]
        checkpoint_step = payload["checkpoint_step"]
    except KeyError as exc:
        raise ValueError(f"prediction row is missing {exc.args[0]}") from exc
    if model_family == ModelFamily.QWEN:
        decoder = payload.get("decoder")
        if not isinstance(decoder, Mapping):
            raise ValueError("Qwen prediction row requires its immutable decoder record")
        try:
            return Phase40PredictionRow(
                validation_row_id=validation_row_id,
                sequence_index=sequence_index,
                gold_label=gold_label,
                raw_prediction=payload["raw_prediction"],
                parsed_state=PredictionState(payload["parsed_state"]),
                parser_exception=payload.get("parser_exception"),
                artifact_identity=artifact_identity,
                checkpoint_step=checkpoint_step,
                decoder_do_sample=decoder["do_sample"],
                decoder_num_return_sequences=decoder["num_return_sequences"],
                decoder_max_new_tokens=decoder["max_new_tokens"],
            )
        except KeyError as exc:
            raise ValueError(f"Qwen prediction row is missing {exc.args[0]}") from exc

    logits = payload.get("logits")
    if (
        not isinstance(logits, list)
        or len(logits) != len(LABEL_ORDER)
        or any(isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) for value in logits)
    ):
        raise ValueError("PhoBERT prediction row requires four finite raw logits")
    predicted = payload.get("argmax_state", payload.get("predicted_label"))
    if predicted not in LABEL_ORDER:
        raise ValueError("PhoBERT prediction row requires a locked argmax state")
    if LABEL_ORDER[max(range(len(logits)), key=lambda index: logits[index])] != predicted:
        raise ValueError("PhoBERT argmax state does not match retained raw logits")
    raw_prediction = json.dumps(
        {"label": predicted}, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )
    return Phase40PredictionRow.from_raw(
        validation_row_id=validation_row_id,
        sequence_index=sequence_index,
        gold_label=gold_label,
        raw_prediction=raw_prediction,
        artifact_identity=artifact_identity,
        checkpoint_step=checkpoint_step,
    )


def _load_prediction_rows_for_checkpoint(
    run_root: Path,
    evidence: RunEvidence,
    checkpoint: Any,
) -> tuple[Phase40PredictionRow, ...]:
    prediction_artifact = _artifact_for_sha(
        evidence, "predictions", checkpoint.predictions_sha256
    )
    payload = _read_json_or_jsonl(
        run_root / prediction_artifact.relative_path,
        description=f"run {evidence.run_id} selected predictions",
    )
    if isinstance(payload, dict):
        rows_payload = payload.get("predictions")
    else:
        rows_payload = payload
    if not isinstance(rows_payload, list) or not rows_payload:
        raise RuntimeError("selected prediction payload must be a non-empty ordered row list")
    rows = tuple(
        _prediction_row_from_payload(row, model_family=evidence.experiment_identity.model_family)
        if isinstance(row, Mapping)
        else (_ for _ in ()).throw(ValueError("prediction row must be one JSON object"))
        for row in rows_payload
    )
    if any(
        row.checkpoint_step != checkpoint.optimizer_step
        or row.artifact_identity != checkpoint.artifact_identity
        for row in rows
    ):
        raise RuntimeError("prediction rows differ from their checkpoint identity")
    return rows


def _load_selected_prediction_bundle(
    run_root: Path,
    evidence: RunEvidence,
) -> "SelectedPredictionBundle":
    if evidence.selected_checkpoint is None:
        raise RuntimeError(f"run {evidence.run_id} has no selected checkpoint")
    selected_candidate = tuple(
        checkpoint
        for checkpoint in evidence.validation_checkpoints
        if checkpoint.optimizer_step == evidence.selected_checkpoint.optimizer_step
        and checkpoint.artifact_identity == evidence.selected_checkpoint.artifact_identity
    )
    if len(selected_candidate) != 1:
        raise RuntimeError(f"run {evidence.run_id} selected checkpoint record is ambiguous")
    rows = _load_prediction_rows_for_checkpoint(
        run_root, evidence, selected_candidate[0]
    )
    model_artifact = _exact_artifact_for_role(evidence, "model_artifact")
    return SelectedPredictionBundle(
        model_run_id=evidence.run_id,
        model_artifact_identity=f"sha256:{model_artifact.sha256}",
        selected_checkpoint_identity=evidence.selected_checkpoint.artifact_identity,
        predictions=rows,
    )


def _metric_summary(metrics: Phase40MetricResult) -> dict[str, Any]:
    return {
        "evaluated_rows": metrics.evaluated_rows,
        "per_class": [asdict(row) for row in metrics.per_class],
        "macro_f1": metrics.macro_f1,
        "weighted_f1": metrics.weighted_f1,
        "accuracy": metrics.accuracy,
        "invalid_output_count": metrics.invalid_output_count,
        "invalid_output_rate": metrics.invalid_output_rate,
        "risky_to_benign_count": metrics.risky_to_benign_count,
        "risky_to_invalid_count": metrics.risky_to_invalid_count,
        "confusion_matrix": [list(row) for row in metrics.confusion_matrix],
        "risky_to_benign_row_ids": list(metrics.risky_to_benign_row_ids),
        "risky_to_invalid_row_ids": list(metrics.risky_to_invalid_row_ids),
    }


def _run_metric_summary(metrics: Phase40MetricResult) -> dict[str, float]:
    by_label = {row.label: row for row in metrics.per_class}
    summary = {
        "accuracy": metrics.accuracy,
        "invalid_output_count": float(metrics.invalid_output_count),
        "invalid_output_rate": metrics.invalid_output_rate,
        "macro_f1": metrics.macro_f1,
        "risky_to_benign_count": float(metrics.risky_to_benign_count),
        "risky_to_invalid_count": float(metrics.risky_to_invalid_count),
        "weighted_f1": metrics.weighted_f1,
    }
    summary.update(
        {f"recall_{label}": by_label[label].recall for label in RISKY_RECALL_FLOORS}
    )
    return dict(sorted(summary.items()))


def _recompute_checkpoint_selection(
    run_root: Path,
    evidence: RunEvidence,
    snapshot: CanonicalSplitSnapshot,
) -> tuple[CheckpointSelection, dict[tuple[int, str], Phase40MetricResult]]:
    candidates: list[Phase40MetricResult] = []
    by_key: dict[tuple[int, str], Phase40MetricResult] = {}
    gold = tuple(row.record.label for row in snapshot.rows)
    for checkpoint in evidence.validation_checkpoints:
        rows = _load_prediction_rows_for_checkpoint(run_root, evidence, checkpoint)
        metrics = evaluate_phase40_predictions(
            expected_validation_row_ids=snapshot.validation_row_ids,
            gold_labels=gold,
            prediction_rows=rows,
        )
        one_candidate_selection = select_phase40_checkpoint((metrics,))
        if (
            metrics.macro_f1 != checkpoint.macro_f1
            or metrics.invalid_output_count != checkpoint.invalid_output_count
            or one_candidate_selection.safety_gate_passed != checkpoint.safety_gate_passed
        ):
            raise RuntimeError("checkpoint summary differs from recomputed prediction metrics")
        metric_artifact = _artifact_for_sha(
            evidence, "metrics", checkpoint.metrics_sha256
        )
        metric_payload = _read_json_or_jsonl(
            run_root / metric_artifact.relative_path,
            description=f"run {evidence.run_id} checkpoint metrics",
        )
        if not isinstance(metric_payload, dict):
            raise RuntimeError("checkpoint metrics artifact must be one JSON object")
        expected_summary = _metric_summary(metrics)
        if metric_payload != expected_summary:
            raise RuntimeError("checkpoint metrics artifact differs from mechanical recomputation")
        key = (checkpoint.optimizer_step, checkpoint.artifact_identity)
        if key in by_key:
            raise RuntimeError("duplicate checkpoint identity in run evidence")
        by_key[key] = metrics
        candidates.append(metrics)
    selected = select_phase40_checkpoint(tuple(candidates))
    persisted = evidence.selected_checkpoint
    if persisted is None or (
        selected.selected_step != persisted.optimizer_step
        or selected.selected_artifact_identity != persisted.artifact_identity
        or selected.safety_gate_passed != persisted.safety_gate_passed
    ):
        raise RuntimeError("selected checkpoint differs from mechanical recomputation")
    return selected, by_key


def _load_resume_config(run_root: Path, evidence: RunEvidence) -> ResumeControlledConfig:
    artifact = _exact_artifact_for_role(evidence, "resolved_config")
    payload = _read_json_or_jsonl(
        run_root / artifact.relative_path,
        description=f"run {evidence.run_id} resolved config",
    )
    if not isinstance(payload, dict):
        raise RuntimeError("resolved config must be one JSON object")
    config = ResumeControlledConfig.model_validate_json(
        json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
    )
    digest = compute_resume_digest(config)
    if digest != evidence.resume_digest:
        raise RuntimeError(f"run {evidence.run_id} resume digest mismatch")
    return config


def _regenerate_graph(
    run_root: Path,
    evidence: RunEvidence,
    *,
    renderer: GraphRenderer | None,
    renderer_name: str | None,
    renderer_version: str | None,
) -> GraphProvenance:
    manifest_artifact = _exact_artifact_for_role(evidence, "graph_manifest")
    original = GraphProvenance.model_validate_json(
        (run_root / manifest_artifact.relative_path).read_text(
            encoding="utf-8", errors="strict"
        )
    )
    kwargs: dict[str, Any] = {
        "events_relative_path": original.event_source.relative_path,
        "metrics_relative_path": original.metrics_source.relative_path,
        "model_artifact_relative_path": original.model_artifact.relative_path,
        "normalized_data_relative_path": original.normalized_data.relative_path,
        "output_relative_path": original.output.relative_path,
        "provenance_relative_path": manifest_artifact.relative_path,
        "smoothing_window": original.options.smoothing_window,
        "dpi": original.options.dpi,
    }
    if renderer is not None:
        kwargs.update(
            renderer=renderer,
            renderer_name=renderer_name,
            renderer_version=renderer_version,
        )
    regenerated = render_phase40_graphs(run_root, **kwargs)
    if regenerated != original:
        raise RuntimeError(f"run {evidence.run_id} graph is not reproducible from raw logs")
    if tuple(evidence.graph_provenance) != (regenerated.as_evidence(),):
        raise RuntimeError(f"run {evidence.run_id} graph provenance differs from run evidence")
    return regenerated


def _comparison_report(manifest: Phase40ComparisonManifest) -> bytes:
    lines = [
        "# Phase 40 Local Two-Full-Model Comparison",
        "",
        f"Status: **{manifest.status}**",
        "",
        "This experiment uses one predeclared training seed (42). It does not estimate run-to-run variance, statistical significance, or stable superiority; no t-test claim is made.",
        "",
    ]
    if manifest.status == "prestart_failed":
        lines.extend((f"Pre-start failure: {manifest.failure_reason}", ""))
        return ("\n".join(lines) + "\n").encode("utf-8")
    lines.extend(
        (
            "Primary execution: local laptop. Colab is validation-only contingency before the held-out boundary is opened.",
            "Training/run evidence remains governed by source-runtime-v3; this amended comparison runs only under its separate hash-pinned local finalizer authority.",
            "Full Qwen LoRA was withdrawn and cancelled before its production run; its bounded local probe is resource evidence only and contributes no predictions.",
            f"LoRA probe: observed_steps={manifest.lora_probe.observed_optimizer_steps}, "
            f"retained_steps={manifest.lora_probe.retained_optimizer_steps}, "
            f"median_step_seconds={manifest.lora_probe.steady_state_step_seconds_median:.3f}, "
            f"peak_VRAM_MiB={manifest.lora_probe.peak_device_vram_used_mib:.1f}, "
            f"minimum_free_VRAM_MiB={manifest.lora_probe.minimum_device_vram_free_mib:.1f}",
            "The probe completed optimizer steps with finite loss and no OOM; the waiver is an operational resource/deadline decision, not a claim that LoRA cannot run.",
            "",
            f"Validation rows per model: {manifest.validation_rows}",
            f"Quality comparison admissible: {manifest.quality_comparison_admissible}",
            f"Hardware-confounded timing/throughput: {manifest.hardware_confounded}",
            f"Speed comparison admissible: {manifest.speed_comparison_admissible}",
            f"Human-review queue rows: {manifest.review_queue_rows}",
            "",
            "## Retained runs",
            "",
        )
    )
    for run in manifest.runs:
        recall_text = ", ".join(
            f"{label}={value:.4f}" for label, value in run.risky_recall_by_label.items()
        )
        package_text = ", ".join(
            f"{name}={version}"
            for name, version in run.package_versions.items()
        )
        tool_pin_text = ", ".join(
            f"{name}={version}"
            for name, version in run.required_tool_pins.items()
        )
        lines.append(
            f"- `{run.run_id}` ({run.model_family.value}/{run.adaptation_mode.value}): "
            f"safety_gate={run.safety_gate_passed}, comparison_eligible={run.comparison_eligible}, "
            f"selected_step={run.selected_optimizer_step}, macro_F1={run.macro_f1:.4f}, "
            f"invalid_outputs={run.invalid_output_count}, risky_recall=[{recall_text}], "
            f"GPU={run.gpu_identity}, exact_run_packages=[{package_text}], "
            f"required_tool_pins=[{tool_pin_text}]"
        )
    lines.extend(
        (
            "",
            "Both submitted complete quality runs are retained, including any failed safety gate; a failed gate is never silently dropped or presented as a deployable winner.",
            "",
        )
    )
    return ("\n".join(lines) + "\n").encode("utf-8")


def verify_phase40_run_request(
    request: RunRequest,
    *,
    repo_root: Path,
    verify_input: bool = True,
) -> RunRequest:
    """Verify both immutable transfer authorities without consulting held-out data."""

    request = request if isinstance(request, RunRequest) else RunRequest.model_validate(request)
    root = _trusted_repo_root(repo_root)
    authority_paths = (
        root / request.source_bundle.repository_relative_archive_path,
        root / request.source_bundle.repository_relative_inventory_path,
        root / request.input_bundle.repository_relative_path,
    )
    _reject_redirecting_path_components(authority_paths)
    verify_phase40_source_bundle(repo_root=root, reference=request.source_bundle)
    if verify_input:
        verify_phase40_input_bundle(
            root / request.input_bundle.repository_relative_path,
            request.input_bundle,
            repo_root=root,
            materialize=False,
        )
    return request


class SelectedPredictionBundle(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, arbitrary_types_allowed=True)

    model_run_id: str
    model_artifact_identity: str = Field(min_length=1)
    selected_checkpoint_identity: str = Field(min_length=1)
    predictions: tuple[Phase40PredictionRow, ...]

    @field_validator("model_run_id")
    @classmethod
    def validate_run_id(cls, value: str) -> str:
        if not _SAFE_RUN_ID_RE.fullmatch(value):
            raise ValueError("model_run_id must be a safe normalized identifier")
        return value

    @model_validator(mode="after")
    def validate_predictions(self) -> "SelectedPredictionBundle":
        if not self.predictions:
            raise ValueError("selected prediction bundle cannot be empty")
        if any(
            row.artifact_identity != self.selected_checkpoint_identity
            for row in self.predictions
        ):
            raise ValueError("prediction artifact identity differs from selected checkpoint")
        return self


class ReviewQueueRow(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    model_run_id: str
    validation_row_id: str
    canonical_sequence: int = Field(ge=0)
    raw_message: str = Field(min_length=1)
    source_row_sha256: str
    gold_label: str
    predicted_label: str
    selected_checkpoint_identity: str = Field(min_length=1)
    model_artifact_identity: str = Field(min_length=1)
    slice_tags: tuple[ReviewSlice, ...]

    @field_validator("source_row_sha256")
    @classmethod
    def validate_hash(cls, value: str) -> str:
        return _require_sha256(value, description="review source row hash")

    @model_validator(mode="after")
    def validate_labels_and_tags(self) -> "ReviewQueueRow":
        if self.gold_label not in LABEL_ORDER:
            raise ValueError("review row gold label is not locked")
        if self.predicted_label not in (*LABEL_ORDER, PredictionState.INVALID_OUTPUT.value):
            raise ValueError("review row prediction is not locked or invalid_output")
        if not self.slice_tags:
            raise ValueError("review queue row requires at least one slice tag")
        ordered = tuple(tag for tag in _SLICE_ORDER if tag in self.slice_tags)
        if ordered != self.slice_tags or len(set(self.slice_tags)) != len(self.slice_tags):
            raise ValueError("review slice tags must be unique and canonically ordered")
        return self

    @property
    def key(self) -> tuple[str, str]:
        return self.model_run_id, self.validation_row_id


def _base_slice_tags(gold: str, predicted: str) -> set[ReviewSlice]:
    tags: set[ReviewSlice] = set()
    if predicted == PredictionState.INVALID_OUTPUT.value:
        tags.add("invalid_output")
    if gold in RISKY_LABELS and predicted == "benign":
        tags.add("risky_to_benign")
    if gold != predicted and "zalo_social_engineering" in (gold, predicted):
        tags.add("zalo_involved_misclassification")
    if gold == "benign" and predicted in RISKY_LABELS:
        tags.add("benign_to_risky")
    if gold in RISKY_LABELS and predicted in RISKY_LABELS and gold != predicted:
        tags.add("risky_cross_confusion")
    return tags


def _prediction_by_snapshot(
    bundle: SelectedPredictionBundle,
    snapshot: CanonicalSplitSnapshot,
) -> tuple[Phase40PredictionRow, ...]:
    expected_ids = snapshot.validation_row_ids
    actual_ids = tuple(row.validation_row_id for row in bundle.predictions)
    if actual_ids != expected_ids:
        raise ValueError(
            f"prediction validation_row_id order differs from canonical snapshot: {bundle.model_run_id}"
        )
    if tuple(row.sequence_index for row in bundle.predictions) != tuple(range(len(snapshot.rows))):
        raise ValueError("prediction sequence indices differ from canonical validation order")
    for source, prediction in zip(snapshot.rows, bundle.predictions, strict=True):
        if prediction.gold_label != source.record.label:
            raise ValueError("prediction gold label differs from immutable validation snapshot")
    return bundle.predictions


def build_phase40_review_queue(
    contract: Phase40DataContract,
    prediction_bundles: Sequence[SelectedPredictionBundle],
) -> tuple[ReviewQueueRow, ...]:
    """Build the deterministic union of required error and calibration slices."""

    if not isinstance(contract, Phase40DataContract):
        raise TypeError("review queue construction requires a Phase40DataContract")
    snapshot = contract.validation_snapshot
    if snapshot.split_name != "val":
        raise ValueError("review queue construction requires a validation snapshot")
    bundles = tuple(prediction_bundles)
    if not bundles or len({bundle.model_run_id for bundle in bundles}) != len(bundles):
        raise ValueError("review queue requires non-empty uniquely identified model bundles")

    tags_by_key: dict[tuple[str, str], set[ReviewSlice]] = {}
    bundle_by_id = {bundle.model_run_id: bundle for bundle in bundles}
    predictions_by_id: dict[str, tuple[Phase40PredictionRow, ...]] = {}
    for bundle in bundles:
        predictions = _prediction_by_snapshot(bundle, snapshot)
        predictions_by_id[bundle.model_run_id] = predictions
        for prediction in predictions:
            key = (bundle.model_run_id, prediction.validation_row_id)
            tags = _base_slice_tags(prediction.gold_label, prediction.parsed_state.value)
            if tags:
                tags_by_key.setdefault(key, set()).update(tags)

        for label in LABEL_ORDER:
            correct = [
                row
                for row in predictions
                if row.gold_label == label and row.parsed_state.value == label
            ]
            correct.sort(
                key=lambda row: hashlib.sha256(
                    (
                        bundle.model_artifact_identity
                        + "\0"
                        + row.validation_row_id
                    ).encode("utf-8")
                ).hexdigest()
            )
            take = max(1, math.ceil(len(correct) * 0.10)) if correct else 0
            for prediction in correct[:take]:
                tags_by_key.setdefault(
                    (bundle.model_run_id, prediction.validation_row_id), set()
                ).add("correct_calibration_sample")

    rows: list[ReviewQueueRow] = []
    source_by_id = {row.snapshot_row_id: row for row in snapshot.rows}
    prediction_lookup = {
        (run_id, row.validation_row_id): row
        for run_id, predictions in predictions_by_id.items()
        for row in predictions
    }
    for key in sorted(
        tags_by_key,
        key=lambda item: (
            tuple(bundle.model_run_id for bundle in bundles).index(item[0]),
            source_by_id[item[1]].canonical_index,
        ),
    ):
        bundle = bundle_by_id[key[0]]
        source = source_by_id[key[1]]
        prediction = prediction_lookup[key]
        rows.append(
            ReviewQueueRow(
                model_run_id=bundle.model_run_id,
                validation_row_id=source.snapshot_row_id,
                canonical_sequence=source.canonical_index,
                raw_message=source.raw_message,
                source_row_sha256=source.source_row_sha256,
                gold_label=source.record.label,
                predicted_label=prediction.parsed_state.value,
                selected_checkpoint_identity=bundle.selected_checkpoint_identity,
                model_artifact_identity=bundle.model_artifact_identity,
                slice_tags=tuple(tag for tag in _SLICE_ORDER if tag in tags_by_key[key]),
            )
        )
    return tuple(rows)


def verify_phase40_review_queue(
    queue_rows: Sequence[ReviewQueueRow],
    *,
    contract: Phase40DataContract,
    prediction_bundles: Sequence[SelectedPredictionBundle],
) -> tuple[ReviewQueueRow, ...]:
    rows = tuple(
        row if isinstance(row, ReviewQueueRow) else ReviewQueueRow.model_validate(row)
        for row in queue_rows
    )
    expected = build_phase40_review_queue(contract, prediction_bundles)
    if rows != expected:
        raise ValueError("review queue differs from immutable snapshot/prediction derivation")
    return rows


class ReviewQueueManifest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["phase40-review-queue-v1"] = PHASE40_REVIEW_QUEUE_SCHEMA_VERSION
    rows: int = Field(gt=0)
    queue_sha256: str
    reviewer_template_sha256: str
    comparison_manifest_sha256: str
    phase39_data_contract_sha256: str
    validation_ordered_row_ids_sha256: str

    @field_validator(
        "queue_sha256",
        "reviewer_template_sha256",
        "comparison_manifest_sha256",
        "phase39_data_contract_sha256",
        "validation_ordered_row_ids_sha256",
    )
    @classmethod
    def validate_hash(cls, value: str) -> str:
        return _require_sha256(value, description="review queue provenance hash")


class ReviewerReturnRow(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    model_run_id: str
    validation_row_id: str
    decision: Literal["confirmed", "questioned", "unclear"]
    note_vi: str = Field(min_length=1, max_length=2000)

    @field_validator("note_vi")
    @classmethod
    def validate_note(cls, value: str) -> str:
        stripped = " ".join(value.split())
        if not stripped:
            raise ValueError("review note cannot be blank")
        if _SECRET_RE.search(stripped) or _WINDOWS_ABSOLUTE_RE.search(stripped):
            raise ValueError("review note contains secret or personal-path material")
        return stripped

    @property
    def key(self) -> tuple[str, str]:
        return self.model_run_id, self.validation_row_id


@dataclass(frozen=True, slots=True)
class HumanReviewArtifacts:
    notes_path: Path
    manifest_path: Path
    report_path: Path


def _queue_jsonl(rows: Sequence[ReviewQueueRow]) -> bytes:
    return b"".join(
        _canonical_json_bytes(row.model_dump(mode="json")) for row in rows
    )


def _review_jsonl(rows: Sequence[ReviewerReturnRow]) -> bytes:
    return b"".join(
        _canonical_json_bytes(row.model_dump(mode="json")) for row in rows
    )


def _selected_prediction_bundles_bytes(
    bundles: Sequence[SelectedPredictionBundle],
) -> bytes:
    payload = [
        {
            "model_run_id": bundle.model_run_id,
            "model_artifact_identity": bundle.model_artifact_identity,
            "selected_checkpoint_identity": bundle.selected_checkpoint_identity,
            "predictions": [row.as_json_dict() for row in bundle.predictions],
        }
        for bundle in bundles
    ]
    return _canonical_json_bytes(payload)


def load_phase40_selected_prediction_bundles(
    path: Path,
    *,
    comparison_manifest: Phase40ComparisonManifest,
) -> tuple[SelectedPredictionBundle, ...]:
    payload_bytes = Path(path).read_bytes()
    if (
        comparison_manifest.selected_prediction_bundles_sha256 is None
        or _sha256(payload_bytes)
        != comparison_manifest.selected_prediction_bundles_sha256
    ):
        raise ValueError("selected prediction bundle artifact hash mismatch")
    try:
        payload = json.loads(payload_bytes.decode("utf-8", errors="strict"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("selected prediction bundle artifact is not strict JSON") from exc
    if not isinstance(payload, list) or len(payload) != len(comparison_manifest.runs):
        raise ValueError("selected prediction bundle artifact has the wrong model count")
    family_by_run = {run.run_id: run.model_family for run in comparison_manifest.runs}
    bundles: list[SelectedPredictionBundle] = []
    for item in payload:
        if not isinstance(item, dict):
            raise ValueError("selected prediction bundle entry must be one object")
        run_id = item.get("model_run_id")
        if run_id not in family_by_run:
            raise ValueError("selected prediction bundle contains an unknown run ID")
        predictions = item.get("predictions")
        if not isinstance(predictions, list):
            raise ValueError("selected prediction bundle predictions must be a list")
        bundles.append(
            SelectedPredictionBundle(
                model_run_id=run_id,
                model_artifact_identity=item.get("model_artifact_identity"),
                selected_checkpoint_identity=item.get("selected_checkpoint_identity"),
                predictions=tuple(
                    _prediction_row_from_payload(row, model_family=ModelFamily.QWEN)
                    if isinstance(row, Mapping)
                    else (_ for _ in ()).throw(
                        ValueError("selected prediction row must be one object")
                    )
                    for row in predictions
                ),
            )
        )
    if tuple(bundle.model_run_id for bundle in bundles) != tuple(
        run.run_id for run in comparison_manifest.runs
    ):
        raise ValueError("selected prediction bundles are reordered")
    return tuple(bundles)


def finalize_phase40_human_review(
    queue_rows: Sequence[ReviewQueueRow],
    reviewer_rows: Sequence[ReviewerReturnRow],
    *,
    request: RunRequest,
    repo_root: Path,
    contract: Phase40DataContract,
    prediction_bundles: Sequence[SelectedPredictionBundle],
    queue_manifest_path: Path,
    comparison_manifest_path: Path,
    scope_amendment_path: Path,
    output_root: Path,
    vietnamese_fluent_attestation: bool,
    verify_only: bool = False,
) -> HumanReviewArtifacts:
    canonical_request = require_canonical_phase40_run_request(
        request,
        repo_root=repo_root,
    )
    amendment = load_frozen_phase40_scope_amendment(
        request=canonical_request,
        repo_root=repo_root,
        amendment_path=scope_amendment_path,
    )
    amendment_bytes = _lexical_absolute(scope_amendment_path).read_bytes()
    if vietnamese_fluent_attestation is not True:
        raise ValueError("human review requires a Vietnamese-fluent reviewer attestation")
    queue = tuple(
        row if isinstance(row, ReviewQueueRow) else ReviewQueueRow.model_validate(row)
        for row in queue_rows
    )
    verify_phase40_review_queue(
        queue,
        contract=contract,
        prediction_bundles=prediction_bundles,
    )
    reviews = tuple(
        row if isinstance(row, ReviewerReturnRow) else ReviewerReturnRow.model_validate(row)
        for row in reviewer_rows
    )
    queue_keys = tuple(row.key for row in queue)
    review_keys = tuple(row.key for row in reviews)
    if len(set(queue_keys)) != len(queue_keys):
        raise ValueError("review queue contains duplicate model-row keys")
    if review_keys != queue_keys or len(set(review_keys)) != len(review_keys):
        raise ValueError("reviewer return must cover every queue key exactly in canonical order")

    queue_bytes = _queue_jsonl(queue)
    notes_bytes = _review_jsonl(reviews)
    comparison_bytes = Path(comparison_manifest_path).read_bytes()
    comparison = Phase40ComparisonManifest.model_validate_json(comparison_bytes)
    if comparison.status != "complete":
        raise ValueError("human review requires a complete comparison manifest")
    if (
        _sha256(amendment_bytes) != comparison.scope_amendment_sha256
        or amendment.original_run_request_sha256 != comparison.original_run_request_sha256
        or amendment.active_full_run_ids
        != tuple(run.run_id for run in comparison.runs)
        or amendment.review_model_run_ids != amendment.active_full_run_ids
        or amendment.lora_probe_authority.sha256
        != comparison.lora_probe.evidence_authority_sha256
        or amendment.comparison_finalizer_authority.source_tree_sha256
        != comparison.comparison_finalizer_source_sha256
    ):
        raise ValueError("human review scope differs from the frozen two-model amendment")
    if (
        comparison.selected_prediction_bundles_sha256 is None
        or _sha256(_selected_prediction_bundles_bytes(prediction_bundles))
        != comparison.selected_prediction_bundles_sha256
    ):
        raise ValueError("human-review predictions differ from the frozen comparison")
    queue_manifest = ReviewQueueManifest.model_validate_json(
        Path(queue_manifest_path).read_text(encoding="utf-8", errors="strict")
    )
    if (
        queue_manifest.rows != len(queue)
        or queue_manifest.queue_sha256 != _sha256(queue_bytes)
        or queue_manifest.comparison_manifest_sha256 != _sha256(comparison_bytes)
        or queue_manifest.phase39_data_contract_sha256 != _contract_identity(contract)
        or queue_manifest.validation_ordered_row_ids_sha256
        != _ordered_row_ids_sha256(contract.validation_snapshot)
    ):
        raise ValueError("review queue provenance differs from comparison/input authorities")
    manifest = {
        "schema_version": PHASE40_HUMAN_REVIEW_SCHEMA_VERSION,
        "vietnamese_fluent_attestation": True,
        "rows": len(queue),
        "queue_sha256": _sha256(queue_bytes),
        "notes_sha256": _sha256(notes_bytes),
        "comparison_manifest_sha256": _sha256(comparison_bytes),
        "scope_amendment_sha256": _sha256(amendment_bytes),
        "review_queue_manifest_sha256": _sha256(Path(queue_manifest_path).read_bytes()),
        "phase39_data_contract_sha256": _contract_identity(contract),
        "validation_ordered_row_ids_sha256": _ordered_row_ids_sha256(
            contract.validation_snapshot
        ),
        "frozen_results_sha256": _sha256(
            _canonical_json_bytes(
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
    }
    manifest_bytes = _canonical_json_bytes(manifest)
    report_lines = [
        "# Phase 40 Vietnamese Validation Review",
        "",
        f"Reviewed rows: {len(queue)}",
        "",
        "The notes are observational only; frozen labels, predictions, and checkpoint selection were not edited.",
        "",
    ]
    for queue_row, review in zip(queue, reviews, strict=True):
        report_lines.append(
            f"- `{queue_row.model_run_id}` / `{queue_row.validation_row_id}`: "
            f"**{review.decision}** — {review.note_vi}"
        )
    report_bytes = ("\n".join(report_lines) + "\n").encode("utf-8")
    root = Path(output_root)
    artifacts = HumanReviewArtifacts(
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
        _write_frozen_bytes(path, payload)
    return artifacts


def write_phase40_review_queue(
    queue_rows: Sequence[ReviewQueueRow],
    *,
    output_root: Path,
    comparison_manifest_sha256: str,
    phase39_data_contract_sha256: str,
    validation_ordered_row_ids_sha256: str,
    verify_only: bool = False,
) -> tuple[Path, Path, Path]:
    rows = tuple(queue_rows)
    if not rows:
        raise ValueError("review queue cannot be empty")
    queue_bytes = _queue_jsonl(rows)
    template_bytes = b"".join(
        _canonical_json_bytes(
            {
                "model_run_id": row.model_run_id,
                "validation_row_id": row.validation_row_id,
                "decision": "unclear",
                "note_vi": "",
            }
        )
        for row in rows
    )
    manifest = ReviewQueueManifest(
        rows=len(rows),
        queue_sha256=_sha256(queue_bytes),
        reviewer_template_sha256=_sha256(template_bytes),
        comparison_manifest_sha256=comparison_manifest_sha256,
        phase39_data_contract_sha256=phase39_data_contract_sha256,
        validation_ordered_row_ids_sha256=validation_ordered_row_ids_sha256,
    )
    manifest_bytes = _canonical_json_bytes(manifest.model_dump(mode="json"))
    root = Path(output_root)
    queue_path = root / "review-queue.jsonl"
    manifest_path = root / "review-queue-manifest.json"
    template_path = root / "reviewer-return.template.jsonl"
    payloads = (
        (queue_path, queue_bytes),
        (manifest_path, manifest_bytes),
        (template_path, template_bytes),
    )
    if verify_only:
        for path, payload in payloads:
            if not path.is_file() or path.read_bytes() != payload:
                raise ValueError(f"review-queue artifact verification failed: {path}")
        return queue_path, manifest_path, template_path
    for path, payload in payloads:
        _write_frozen_bytes(path, payload)
    return queue_path, manifest_path, template_path


def _authorized_return_roots(
    request: RunRequest,
    operator_return: LocalTwoModelOperatorReturn,
    amendment: Phase40ScopeAmendment,
    *,
    repo_root: Path,
) -> dict[str, Path]:
    """Validate every identity/path mapping before opening any returned root."""

    request_by_id = {
        run.run_id: run
        for run in request.runs
        if run.run_id in amendment.active_full_run_ids
    }
    returned_by_id = {root.run_id: root for root in operator_return.bundle_roots}
    gpu_ids = {gpu.run_id for gpu in operator_return.gpu_identities}
    if set(returned_by_id) != set(request_by_id) or gpu_ids != set(request_by_id):
        raise ValueError("operator return run IDs differ from the amended two-model scope")
    root = Path(os.path.abspath(os.path.normpath(os.fspath(repo_root))))
    authorized: dict[str, Path] = {}
    for run_id, requested in request_by_id.items():
        returned = returned_by_id[run_id]
        if returned.path != requested.returned_root:
            raise ValueError("operator returned root differs from its request-bound run identity")
        expected = Path(
            os.path.abspath(os.path.normpath(os.fspath(root / requested.returned_root)))
        )
        supplied = Path(
            os.path.abspath(os.path.normpath(os.fspath(root / returned.path)))
        )
        if supplied != expected:
            raise ValueError("operator returned root is not request-bound")
        authorized[run_id] = supplied
    return authorized


def _write_or_verify_comparison_payloads(
    *,
    output_root: Path,
    manifest: Phase40ComparisonManifest,
    verify_only: bool,
) -> tuple[Path, Path]:
    manifest_path = Path(output_root) / "comparison-manifest.json"
    report_path = Path(output_root) / "comparison-report.md"
    manifest_bytes = _canonical_json_bytes(manifest.model_dump(mode="json"))
    report_bytes = _comparison_report(manifest)
    if verify_only:
        for path, payload in (
            (manifest_path, manifest_bytes),
            (report_path, report_bytes),
        ):
            if not path.is_file() or path.read_bytes() != payload:
                raise ValueError(f"comparison artifact verification failed: {path}")
        return manifest_path, report_path
    _write_frozen_bytes(manifest_path, manifest_bytes)
    _write_frozen_bytes(report_path, report_bytes)
    return manifest_path, report_path


def finalize_phase40_comparison(
    request: RunRequest,
    operator_return: LocalTwoModelOperatorReturn,
    *,
    repo_root: Path,
    scope_amendment_path: Path,
    output_root: Path,
    verify_only: bool = False,
    bundle_verifier: Callable[[Path], RunEvidence] = verify_phase40_bundle,
    renderer: GraphRenderer | None = None,
    renderer_name: str | None = None,
    renderer_version: str | None = None,
) -> ComparisonArtifacts:
    """Re-verify QLoRA and PhoBERT plus the resource-only LoRA probe."""

    request = request if isinstance(request, RunRequest) else RunRequest.model_validate(request)
    request = require_canonical_phase40_run_request(
        request,
        repo_root=repo_root,
    )
    operator_return = (
        operator_return
        if isinstance(operator_return, LocalTwoModelOperatorReturn)
        else LocalTwoModelOperatorReturn.model_validate(operator_return)
    )
    amendment = load_frozen_phase40_scope_amendment(
        request=request,
        repo_root=repo_root,
        amendment_path=scope_amendment_path,
    )
    lora_probe = verify_phase40_scope_amendment(
        amendment,
        request=request,
        repo_root=repo_root,
    )
    amendment_payload = _lexical_absolute(scope_amendment_path).read_bytes()
    amendment_sha256 = _sha256(amendment_payload)
    # This lexical identity/path gate intentionally precedes every root read.
    authorized_roots = _authorized_return_roots(
        request, operator_return, amendment, repo_root=Path(repo_root)
    )
    _reject_redirecting_path_components(tuple(authorized_roots.values()))

    verify_phase40_source_bundle(repo_root=repo_root, reference=request.source_bundle)
    contract = verify_phase40_input_bundle(
        Path(repo_root) / request.input_bundle.repository_relative_path,
        request.input_bundle,
        repo_root=repo_root,
        materialize=False,
    )
    validation_rows = len(contract.validation_snapshot.rows)
    if validation_rows != request.input_bundle.data_members[1].records:
        raise RuntimeError("verified validation row count differs from the run request")
    if validation_rows != 219:
        raise RuntimeError("Phase 40 comparison requires exactly 219 validation rows per model")

    limitations = (
        "single_training_seed_42_no_variance_or_significance_claim",
        "validation_only_no_held_out_test_claim",
        "zalo_validation_support_is_small_and_all_zalo_errors_require_review",
        "full_lora_cancelled_before_start_after_bounded_local_resource_probe",
        "lora_probe_has_no_predictions_and_supports_no_quality_claim",
        "colab_is_validation_contingency_only_before_held_out_open",
    )
    request_by_id = {run.run_id: run for run in request.runs}
    gpu_by_id = {gpu.run_id: gpu for gpu in operator_return.gpu_identities}
    active_requests = tuple(
        request_by_id[run_id] for run_id in amendment.active_full_run_ids
    )
    prediction_bundles: list[SelectedPredictionBundle] = []
    run_records: list[ComparisonRunRecord] = []
    expected_transfer_authority = transfer_authority_from_request(request)
    for requested in active_requests:
        run_root = authorized_roots[requested.run_id]
        if not run_root.is_dir() or run_root.is_symlink():
            raise RuntimeError(f"returned run root is missing or unsafe: {requested.run_id}")
        for required in request.expected_bundle_files:
            required_path = run_root / PurePosixPath(required)
            if not required_path.exists() or required_path.is_symlink():
                raise RuntimeError(
                    f"returned run {requested.run_id} is missing required output: {required}"
                )
            if required_path.is_file() and required_path.stat().st_size == 0:
                raise RuntimeError(
                    f"returned run {requested.run_id} has an empty required output: {required}"
                )
        evidence = bundle_verifier(run_root)
        if not isinstance(evidence, RunEvidence):
            evidence = RunEvidence.model_validate(evidence)
        if evidence.status != EvidenceStatus.COMPLETE or evidence.run_kind != RunKind.FULL:
            raise RuntimeError(f"returned run is not complete full evidence: {requested.run_id}")
        if evidence.run_id != requested.run_id:
            raise RuntimeError("returned run ID differs from the request")
        if evidence.transfer_authority != expected_transfer_authority:
            raise RuntimeError("returned run transfer authority differs from the frozen request")
        identity = evidence.experiment_identity
        if (
            identity.model_family != requested.model_family
            or identity.adaptation_mode != requested.adaptation_mode
            or identity.run_kind != RunKind.FULL
        ):
            raise RuntimeError("returned run experiment identity differs from the request")
        graph = _regenerate_graph(
            run_root,
            evidence,
            renderer=renderer,
            renderer_name=renderer_name,
            renderer_version=renderer_version,
        )
        if graph.renderer != "matplotlib" or graph.renderer_version != "3.11.1":
            raise RuntimeError(
                "returned run graph evidence is not pinned to matplotlib 3.11.1"
            )
        evidence = bundle_verifier(run_root)
        config = _load_resume_config(run_root, evidence)
        request.control_template_by_run[requested.run_id].verify_runtime_config(config)
        if evidence.model_revision != config.model_revision:
            raise RuntimeError("returned model revision differs from the controlled config")
        for split, member in zip(evidence.splits, request.input_bundle.data_members, strict=True):
            if (
                split.logical_name != member.logical_name
                or split.records != member.records
                or split.bytes != member.bytes
                or split.sha256 != member.sha256
                or split.ordered_row_ids_sha256 != member.ordered_row_ids_sha256
            ):
                raise RuntimeError("returned evidence split identity differs from the input request")
        gpu = gpu_by_id[requested.run_id]
        if gpu.accelerator != config.accelerator.accelerator_name:
            raise RuntimeError("operator GPU identity differs from the controlled run config")
        recomputed_selection, recomputed_metrics = _recompute_checkpoint_selection(
            run_root, evidence, contract.validation_snapshot
        )
        prediction_bundle = _load_selected_prediction_bundle(run_root, evidence)
        _prediction_by_snapshot(prediction_bundle, contract.validation_snapshot)
        if len(prediction_bundle.predictions) != validation_rows:
            raise RuntimeError("returned selected predictions do not cover all validation rows")
        selected = evidence.selected_checkpoint
        assert selected is not None
        selected_metrics = recomputed_metrics[
            (recomputed_selection.selected_step, recomputed_selection.selected_artifact_identity)
        ]
        expected_run_metrics = _run_metric_summary(selected_metrics)
        if evidence.validation_metrics != expected_run_metrics:
            raise RuntimeError("run-level validation metrics differ from selected raw predictions")
        risky_recall = {
            label: next(row.recall for row in selected_metrics.per_class if row.label == label)
            for label in RISKY_RECALL_FLOORS
        }
        required_tool_pins = {"matplotlib": graph.renderer_version}
        if identity.adaptation_mode == AdaptationMode.QLORA:
            if (
                evidence.quantization is None
                or evidence.quantization.resolved_mode
                != ResolvedQwenMode.FOUR_BIT_QLORA
                or evidence.quantization.bitsandbytes_version != "0.50.1"
                or evidence.package_versions.get("bitsandbytes") != "0.50.1"
            ):
                raise RuntimeError(
                    "QLoRA run evidence is not pinned to bitsandbytes 0.50.1"
                )
            required_tool_pins["bitsandbytes"] = (
                evidence.quantization.bitsandbytes_version
            )
        prediction_bundles.append(prediction_bundle)
        evidence_path = run_root / "run-evidence.json"
        run_records.append(
            ComparisonRunRecord(
                run_id=evidence.run_id,
                model_family=identity.model_family,
                adaptation_mode=identity.adaptation_mode,
                returned_root=request_by_id[evidence.run_id].returned_root,
                evidence_sha256=build_model_checksum(evidence_path),
                resume_digest=evidence.resume_digest,
                selected_checkpoint_identity=selected.artifact_identity,
                selected_optimizer_step=selected.optimizer_step,
                safety_gate_passed=selected.safety_gate_passed,
                comparison_eligible=evidence.comparison_eligible,
                validation_rows=len(prediction_bundle.predictions),
                validation_metrics=evidence.validation_metrics,
                macro_f1=selected_metrics.macro_f1,
                invalid_output_count=selected_metrics.invalid_output_count,
                risky_recall_by_label=risky_recall,
                gpu_identity=gpu.accelerator,
                package_versions=evidence.package_versions,
                required_tool_pins=required_tool_pins,
            )
        )

    bundles = tuple(prediction_bundles)
    queue = build_phase40_review_queue(contract, bundles)
    if not queue:
        raise RuntimeError("verified comparison produced an empty human-review queue")
    queue_sha256 = _sha256(_queue_jsonl(queue))
    selected_bundles_bytes = _selected_prediction_bundles_bytes(bundles)
    all_runs_admissible = all(
        run.comparison_eligible and run.safety_gate_passed for run in run_records
    )
    quality_admissible = all_runs_admissible
    active_gpu_names = tuple(gpu_by_id[run.run_id].accelerator for run in active_requests)
    hardware_confounded = len(set(active_gpu_names)) != 1
    manifest = Phase40ComparisonManifest(
        status="complete",
        package_decisions=operator_return.package_decisions,
        original_run_request_sha256=amendment.original_run_request_sha256,
        scope_amendment_sha256=amendment_sha256,
        comparison_finalizer_source_sha256=(
            amendment.comparison_finalizer_authority.source_tree_sha256
        ),
        lora_probe=lora_probe,
        source_archive_sha256=request.source_bundle.archive_sha256,
        source_inventory_sha256=request.source_bundle.inventory_sha256,
        input_archive_sha256=request.input_bundle.archive_sha256,
        input_manifest_sha256=request.input_bundle.manifest_sha256,
        validation_rows=validation_rows,
        runs=tuple(run_records),
        qwen_config_comparison=None,
        quality_comparison_admissible=quality_admissible,
        hardware_confounded=hardware_confounded,
        speed_comparison_admissible=False,
        review_queue_rows=len(queue),
        review_queue_sha256=queue_sha256,
        selected_prediction_bundles_sha256=_sha256(selected_bundles_bytes),
        limitations=limitations,
        failure_reason=None,
    )
    manifest_path, report_path = _write_or_verify_comparison_payloads(
        output_root=output_root, manifest=manifest, verify_only=verify_only
    )
    selected_bundles_path = Path(output_root) / "selected-prediction-bundles.json"
    if verify_only:
        if (
            not selected_bundles_path.is_file()
            or selected_bundles_path.read_bytes() != selected_bundles_bytes
        ):
            raise ValueError("selected prediction bundle artifact verification failed")
    else:
        _write_frozen_bytes(selected_bundles_path, selected_bundles_bytes)
    queue_path, queue_manifest_path, template_path = write_phase40_review_queue(
        queue,
        output_root=Path(output_root) / "review",
        comparison_manifest_sha256=_sha256(
            _canonical_json_bytes(manifest.model_dump(mode="json"))
        ),
        phase39_data_contract_sha256=_contract_identity(contract),
        validation_ordered_row_ids_sha256=_ordered_row_ids_sha256(
            contract.validation_snapshot
        ),
        verify_only=verify_only,
    )
    return ComparisonArtifacts(
        manifest_path,
        report_path,
        queue_path,
        queue_manifest_path,
        template_path,
        selected_bundles_path,
        manifest,
        bundles,
    )
