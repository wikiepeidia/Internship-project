"""Build and verify the immutable Phase 40 PhoBERT inference bundle.

The training run remains untouched.  A successful build publishes a new,
write-once directory containing only the selected classifier, the exact
tokenizer, and the authorities needed to explain their provenance.  All source
trees are held under Windows non-delete/non-write-shared handles for the whole
verification and copy operation; the published tree is independently hashed
and verified before it is returned to a caller.
"""

from __future__ import annotations

from contextlib import ExitStack
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
from types import MappingProxyType
from typing import Mapping, Sequence
import uuid

from pydantic import ValidationError

from src.model_adaptation import phase40_final_authority as _final_authority
from src.model_adaptation.phase40_evidence import (
    EvidenceStatus,
    ResumeControlledConfig,
    RunEvidence,
    verify_phase40_bundle,
)
from src.model_adaptation.phase40_handoff import (
    FIXED_INPUT_DRIVE_PATH,
    FIXED_INPUT_EXTRACTION_ROOT,
    transfer_authority_from_request,
)
from src.model_adaptation.phase40_modes import AdaptationMode, ModelFamily, RunKind
from src.model_adaptation.phase40_release_authorities import (
    ReleaseAuthorityError,
    _WindowsClosedTreeLease,
    canonical_json_bytes,
)
from src.model_adaptation.phobert_training import (
    PHOBERT_BASE_MODEL_MANIFEST_NAME,
    PHOBERT_BASE_PROVENANCE_SCHEMA,
    PHOBERT_MODEL_ID,
    PHOBERT_MODEL_REVISION,
    PhoBertBaseModelProvenance,
    _model_state_identity as _phobert_model_state_identity,
)
from src.model_adaptation.registry import build_model_checksum


PHOBERT_RELEASE_SCHEMA_VERSION = "phase40-phobert-release-bundle-v2"
PHOBERT_RELEASE_RECEIPT_SCHEMA_VERSION = "phase40-phobert-tokenizer-authority-v2"
PHOBERT_RELEASE_MANIFEST_NAME = "phobert-release-manifest.json"
PHOBERT_RELEASE_RUN_EVIDENCE_NAME = "run-evidence.json"
PHOBERT_RELEASE_RESOLVED_CONFIG_NAME = "resolved-config.json"
PHOBERT_RELEASE_TRAINER_STATE_NAME = "trainer-state.json"
PHOBERT_RELEASE_MODEL_ROOT = "model-artifact"
PHOBERT_RELEASE_TOKENIZER_ROOT = "tokenizer"
PHOBERT_RELEASE_BUNDLE_RELATIVE_PATH = "data/models/phase40/inference/phobert"
PHOBERT_RELEASE_RECEIPT_RELATIVE_PATH = (
    "data/models/phase40/phobert-tokenizer-authority.json"
)
PHOBERT_RELEASE_ORIGIN_REQUEST_RELATIVE_PATH = (
    f"{_final_authority.FIXED_PHOBERT_V12_CAPSULE_ROOT}/"
    f"{_final_authority.FIXED_ORIGINAL_REQUEST_PATH}"
)

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_CHECKPOINT_ID_RE = re.compile(r"^model-state-sha256:[0-9a-f]{64}$")
_PERSONAL_ABSOLUTE_PATH_RE = re.compile(
    r"(?i)(?<![0-9A-Za-z])(?:[A-Z]:[\\/]|\\\\)"
    r"|(?<![0-9A-Za-z:/<])/(?!/)"
)
_LOCAL_FILE_URI_RE = re.compile(
    r"(?i)(?<![A-Za-z0-9+.-])file:(?://|/|\\\\|[A-Z]:)"
)
_PORTABLE_JSON_SUFFIXES = frozenset({".json"})
_PORTABLE_JSONL_SUFFIXES = frozenset({".jsonl"})
_PORTABLE_TEXT_SUFFIXES = frozenset(
    {
        ".cfg",
        ".conf",
        ".ini",
        ".md",
        ".py",
        ".toml",
        ".yaml",
        ".yml",
    }
)
_OPAQUE_BINARY_SUFFIXES = frozenset(
    {
        ".bin",
        ".model",
        ".npy",
        ".npz",
        ".onnx",
        ".pickle",
        ".pkl",
        ".pt",
        ".pth",
    }
)
_LEXICAL_ASSET_NAMES = frozenset(
    {
        "added_tokens.json",
        "dict.txt",
        "dictionary.txt",
        "merges.json",
        "merges.txt",
        "vocab.json",
        "vocab.txt",
    }
)
_LEXICAL_ASSET_SUFFIXES = frozenset({".bpe", ".merges", ".vocab"})
_SPECIAL_TOKEN_FIELDS = (
    "additional_special_tokens",
    "bos_token",
    "cls_token",
    "eos_token",
    "mask_token",
    "pad_token",
    "sep_token",
    "unk_token",
)
_TOKENIZER_LEXICAL_SUBTREE_PATTERNS = MappingProxyType(
    {
        "special_tokens_map.json": tuple((field,) for field in _SPECIAL_TOKEN_FIELDS),
        "tokenizer.json": (
            ("added_tokens", "[]", "content"),
            ("model", "merges"),
            ("model", "vocab"),
            ("post_processor", "special_tokens", "<key>"),
            ("post_processor", "special_tokens", "*", "content"),
            ("post_processor", "special_tokens", "*", "id"),
            ("post_processor", "special_tokens", "*", "tokens"),
        ),
        "tokenizer_config.json": (
            *((field,) for field in _SPECIAL_TOKEN_FIELDS),
            ("added_tokens_decoder", "*", "content"),
        ),
    }
)
_SAFETENSORS_SUFFIX = ".safetensors"
_MAX_SAFETENSORS_HEADER_BYTES = 64 * 1024 * 1024
_CANONICAL_RUN_EVIDENCE_PATH_EXCEPTIONS = MappingProxyType(
    {
        ("transfer_authority", "input_drive_path"): FIXED_INPUT_DRIVE_PATH,
        ("transfer_authority", "input_extraction_root"): (
            FIXED_INPUT_EXTRACTION_ROOT
        ),
    }
)
_TREE_DOMAIN = b"phase40-phobert-release-tree-v2\0"


class PhoBertReleaseError(ReleaseAuthorityError):
    """The requested release bundle or one of its authorities is unsafe."""


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _require_sha256(value: object, description: str) -> str:
    if not isinstance(value, str) or not _SHA256_RE.fullmatch(value):
        raise PhoBertReleaseError(f"{description} must be a lowercase SHA-256")
    return value


def _require_text(value: object, description: str) -> str:
    if (
        not isinstance(value, str)
        or not value
        or value != value.strip()
        or "\x00" in value
        or any(ord(character) < 32 for character in value)
    ):
        raise PhoBertReleaseError(f"{description} must be canonical non-empty text")
    return value


def _require_nonnegative_int(value: object, description: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise PhoBertReleaseError(f"{description} must be a non-negative integer")
    return value


def _require_positive_int(value: object, description: str) -> int:
    result = _require_nonnegative_int(value, description)
    if result == 0:
        raise PhoBertReleaseError(f"{description} must be positive")
    return result


def _require_exact_keys(
    value: object,
    expected: frozenset[str],
    description: str,
) -> dict[str, object]:
    if not isinstance(value, dict) or set(value) != expected:
        raise PhoBertReleaseError(f"{description} fields differ from schema")
    return value


def _require_relative_path(value: object, description: str) -> str:
    text = _require_text(value, description)
    if "\\" in text or ":" in text or text.startswith("/"):
        raise PhoBertReleaseError(f"{description} is not canonical relative POSIX")
    parts = text.split("/")
    if any(part in {"", ".", ".."} for part in parts):
        raise PhoBertReleaseError(f"{description} is not canonical relative POSIX")
    if PurePosixPath(text).as_posix() != text:
        raise PhoBertReleaseError(f"{description} is not canonical relative POSIX")
    return text


def _reject_duplicate_keys(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise PhoBertReleaseError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _reject_nonfinite(value: str) -> object:
    raise PhoBertReleaseError(f"non-finite JSON value is forbidden: {value}")


def _parse_json_bytes(payload: bytes, description: str) -> object:
    try:
        text = payload.decode("utf-8", errors="strict")
        value = json.loads(
            text,
            object_pairs_hook=_reject_duplicate_keys,
            parse_constant=_reject_nonfinite,
        )
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise PhoBertReleaseError(f"{description} is not strict JSON UTF-8") from exc
    return value


def _field_path_matches(
    field_path: tuple[str, ...],
    pattern: tuple[str, ...],
) -> bool:
    return len(field_path) == len(pattern) and all(
        expected == "*" or expected == observed
        for observed, expected in zip(field_path, pattern, strict=True)
    )


def _reject_absolute_path_leakage(
    value: object,
    description: str,
    *,
    field_path: tuple[str, ...] = (),
    lexical_subtree_patterns: tuple[tuple[str, ...], ...] = (),
    path_exceptions: Mapping[tuple[str, ...], str] | None = None,
) -> None:
    if any(
        _field_path_matches(field_path, pattern)
        for pattern in lexical_subtree_patterns
    ):
        return
    if isinstance(value, str):
        if path_exceptions is not None and path_exceptions.get(field_path) == value:
            return
        if (
            _LOCAL_FILE_URI_RE.search(value)
            or _PERSONAL_ABSOLUTE_PATH_RE.search(value)
        ):
            raise PhoBertReleaseError(f"{description} contains an absolute host path")
        return
    if isinstance(value, Mapping):
        for key, item in value.items():
            _reject_absolute_path_leakage(
                key,
                description,
                field_path=(*field_path, "<key>"),
                lexical_subtree_patterns=lexical_subtree_patterns,
                path_exceptions=path_exceptions,
            )
            _reject_absolute_path_leakage(
                item,
                description,
                field_path=(*field_path, str(key)),
                lexical_subtree_patterns=lexical_subtree_patterns,
                path_exceptions=path_exceptions,
            )
        return
    if isinstance(value, (list, tuple)):
        for item in value:
            _reject_absolute_path_leakage(
                item,
                description,
                field_path=(*field_path, "[]"),
                lexical_subtree_patterns=lexical_subtree_patterns,
                path_exceptions=path_exceptions,
            )


def _reject_portable_payload_path_leakage(
    payload: bytes,
    description: str,
    *,
    lexical_subtree_patterns: tuple[tuple[str, ...], ...] = (),
    relative_path: str,
    path_exceptions: Mapping[tuple[str, ...], str] | None = None,
) -> None:
    suffix = PurePosixPath(relative_path).suffix.lower()
    explicit_text = suffix in (
        _PORTABLE_JSON_SUFFIXES
        | _PORTABLE_JSONL_SUFFIXES
        | _PORTABLE_TEXT_SUFFIXES
    )
    try:
        text = payload.decode("utf-8", errors="strict")
    except UnicodeError as exc:
        if explicit_text:
            raise PhoBertReleaseError(
                f"{description} textual metadata is not strict UTF-8"
            ) from exc
        return
    if "\x00" in text:
        if explicit_text:
            raise PhoBertReleaseError(
                f"{description} textual metadata contains NUL bytes"
            )
        return
    parsed_values: list[object] = []
    if suffix in _PORTABLE_JSONL_SUFFIXES:
        for line_number, line in enumerate(payload.splitlines(), start=1):
            if not line.strip():
                continue
            parsed_values.append(
                _parse_json_bytes(
                    line,
                    f"{description} JSONL line {line_number}",
                )
            )
    elif suffix in _PORTABLE_JSON_SUFFIXES:
        parsed_values.append(_parse_json_bytes(payload, description))
    else:
        try:
            parsed_values.append(_parse_json_bytes(payload, description))
        except PhoBertReleaseError:
            parsed_values.clear()
    if parsed_values:
        for value in parsed_values:
            _reject_absolute_path_leakage(
                value,
                description,
                lexical_subtree_patterns=lexical_subtree_patterns,
                path_exceptions=path_exceptions,
            )
        return
    _reject_absolute_path_leakage(
        text,
        description,
        lexical_subtree_patterns=lexical_subtree_patterns,
        path_exceptions=path_exceptions,
    )


def _load_canonical_json(path: Path, description: str) -> tuple[object, bytes]:
    try:
        payload = path.read_bytes()
    except OSError as exc:
        raise PhoBertReleaseError(f"{description} could not be read") from exc
    if not payload:
        raise PhoBertReleaseError(f"{description} is empty")
    value = _parse_json_bytes(payload, description)
    if canonical_json_bytes(value) != payload:
        raise PhoBertReleaseError(f"{description} is not canonical JSON")
    return value, payload


def _load_json(path: Path, description: str) -> tuple[object, bytes]:
    try:
        payload = path.read_bytes()
    except OSError as exc:
        raise PhoBertReleaseError(f"{description} could not be read") from exc
    if not payload:
        raise PhoBertReleaseError(f"{description} is empty")
    return _parse_json_bytes(payload, description), payload


def _lexical_absolute(path: Path, description: str) -> Path:
    supplied = Path(path)
    raw = os.fspath(supplied)
    if (
        not supplied.is_absolute()
        or "\x00" in raw
        or ".." in supplied.parts
    ):
        raise PhoBertReleaseError(
            f"{description} must be a canonical bounded absolute path"
        )
    absolute = Path(os.path.abspath(os.path.normpath(raw)))
    if absolute.parent == absolute:
        raise PhoBertReleaseError(f"{description} must be bounded")
    return absolute


def _path_key(path: Path) -> str:
    return os.path.normcase(os.fspath(path))


def _same_path(first: Path, second: Path) -> bool:
    return _path_key(first) == _path_key(second)


def _is_within(candidate: Path, root: Path) -> bool:
    try:
        common = os.path.commonpath((os.fspath(candidate), os.fspath(root)))
    except ValueError:
        return False
    return os.path.normcase(common) == os.path.normcase(os.fspath(root))


def _require_disjoint(first: Path, second: Path, description: str) -> None:
    if _is_within(first, second) or _is_within(second, first):
        raise PhoBertReleaseError(f"{description} must be disjoint")


@dataclass(frozen=True, slots=True)
class ReleaseFileRecord:
    relative_path: str
    bytes: int
    sha256: str

    def __post_init__(self) -> None:
        _require_relative_path(self.relative_path, "release file path")
        _require_nonnegative_int(self.bytes, "release file bytes")
        _require_sha256(self.sha256, "release file sha256")

    def as_dict(self) -> dict[str, object]:
        return {
            "relative_path": self.relative_path,
            "bytes": self.bytes,
            "sha256": self.sha256,
        }

    @classmethod
    def from_dict(cls, value: object) -> "ReleaseFileRecord":
        body = _require_exact_keys(
            value,
            frozenset({"relative_path", "bytes", "sha256"}),
            "release file record",
        )
        return cls(
            relative_path=body["relative_path"],  # type: ignore[arg-type]
            bytes=body["bytes"],  # type: ignore[arg-type]
            sha256=body["sha256"],  # type: ignore[arg-type]
        )


def _tree_sha256(
    directories: Sequence[str],
    files: Sequence[ReleaseFileRecord],
) -> str:
    body = {
        "directories": list(directories),
        "files": [item.as_dict() for item in files],
    }
    return _sha256(_TREE_DOMAIN + canonical_json_bytes(body))


@dataclass(frozen=True, slots=True)
class ReleaseTreeAuthority:
    relative_root: str
    directories: tuple[str, ...]
    files: tuple[ReleaseFileRecord, ...]
    tree_sha256: str
    content_sha256: str

    def __post_init__(self) -> None:
        _require_relative_path(self.relative_root, "release tree root")
        if self.directories != tuple(sorted(self.directories)):
            raise PhoBertReleaseError("release tree directories are not sorted")
        if len(set(self.directories)) != len(self.directories):
            raise PhoBertReleaseError("release tree directories are duplicated")
        for directory in self.directories:
            _require_relative_path(directory, "release tree directory")
        paths = tuple(item.relative_path for item in self.files)
        if not paths or paths != tuple(sorted(paths)) or len(set(paths)) != len(paths):
            raise PhoBertReleaseError(
                "release tree files must be non-empty, unique, and sorted"
            )
        if set(paths) & set(self.directories):
            raise PhoBertReleaseError("release tree path ownership is duplicated")
        expected_directories = {
            PurePosixPath(path).parent.as_posix()
            for path in paths
            if PurePosixPath(path).parent.as_posix() != "."
        }
        for directory in tuple(expected_directories):
            parent = PurePosixPath(directory).parent
            while parent.as_posix() != ".":
                expected_directories.add(parent.as_posix())
                parent = parent.parent
        if not expected_directories.issubset(set(self.directories)):
            raise PhoBertReleaseError("release tree omits a file parent directory")
        _require_sha256(self.tree_sha256, "release tree sha256")
        _require_sha256(self.content_sha256, "release tree content sha256")
        if self.tree_sha256 != _tree_sha256(self.directories, self.files):
            raise PhoBertReleaseError("release tree self-hash mismatch")

    def as_dict(self) -> dict[str, object]:
        return {
            "relative_root": self.relative_root,
            "directories": list(self.directories),
            "files": [item.as_dict() for item in self.files],
            "tree_sha256": self.tree_sha256,
            "content_sha256": self.content_sha256,
        }

    @classmethod
    def from_dict(cls, value: object) -> "ReleaseTreeAuthority":
        body = _require_exact_keys(
            value,
            frozenset(
                {
                    "relative_root",
                    "directories",
                    "files",
                    "tree_sha256",
                    "content_sha256",
                }
            ),
            "release tree authority",
        )
        raw_directories = body["directories"]
        raw_files = body["files"]
        if not isinstance(raw_directories, list) or not isinstance(raw_files, list):
            raise PhoBertReleaseError("release tree inventories must be lists")
        return cls(
            relative_root=body["relative_root"],  # type: ignore[arg-type]
            directories=tuple(raw_directories),  # type: ignore[arg-type]
            files=tuple(ReleaseFileRecord.from_dict(item) for item in raw_files),
            tree_sha256=body["tree_sha256"],  # type: ignore[arg-type]
            content_sha256=body["content_sha256"],  # type: ignore[arg-type]
        )


@dataclass(frozen=True, slots=True)
class PhoBertReleaseManifest:
    upstream: Mapping[str, object]
    run: Mapping[str, object]
    selected_model: Mapping[str, object]
    base_model: Mapping[str, object]
    model_tree: ReleaseTreeAuthority
    tokenizer_tree: ReleaseTreeAuthority
    model_id: str
    model_revision: str
    preprocessor_sha256: str
    authority_sha256: str
    schema_version: str = PHOBERT_RELEASE_SCHEMA_VERSION
    role: str = "phobert"

    def __post_init__(self) -> None:
        if self.schema_version != PHOBERT_RELEASE_SCHEMA_VERSION or self.role != "phobert":
            raise PhoBertReleaseError("unsupported PhoBERT release manifest")
        if self.model_id != PHOBERT_MODEL_ID or self.model_revision != PHOBERT_MODEL_REVISION:
            raise PhoBertReleaseError("PhoBERT release model identity drifted")
        _require_sha256(self.preprocessor_sha256, "preprocessor sha256")
        self._validate_upstream()
        self._validate_run()
        self._validate_selected_model()
        self._validate_base_model()
        if self.model_tree.relative_root != PHOBERT_RELEASE_MODEL_ROOT:
            raise PhoBertReleaseError("PhoBERT release model root drifted")
        if self.tokenizer_tree.relative_root != PHOBERT_RELEASE_TOKENIZER_ROOT:
            raise PhoBertReleaseError("PhoBERT release tokenizer root drifted")
        if (
            self.selected_model["artifact_sha256"]
            != self.model_tree.content_sha256
        ):
            raise PhoBertReleaseError("selected artifact and model tree hashes differ")
        expected = _sha256(canonical_json_bytes(self._body_without_hash()))
        if self.authority_sha256 != expected:
            raise PhoBertReleaseError("PhoBERT release manifest self-hash mismatch")
        _reject_absolute_path_leakage(self._body_without_hash(), "release manifest")
        object.__setattr__(self, "upstream", MappingProxyType(dict(self.upstream)))
        object.__setattr__(self, "run", MappingProxyType(dict(self.run)))
        object.__setattr__(
            self,
            "selected_model",
            MappingProxyType(dict(self.selected_model)),
        )
        object.__setattr__(self, "base_model", MappingProxyType(dict(self.base_model)))

    def _validate_upstream(self) -> None:
        body = _require_exact_keys(
            self.upstream,
            frozenset(
                {
                    "final_comparison_authority_relative_path",
                    "final_comparison_authority_sha256",
                    "origin_request_authority_id",
                    "origin_run_request_relative_path",
                    "origin_run_request_sha256",
                    "origin_control_template_sha256",
                    "origin_transfer_authority_sha256",
                }
            ),
            "release upstream authority",
        )
        if (
            body["final_comparison_authority_relative_path"]
            != _final_authority.FIXED_FINAL_COMPARISON_AUTHORITY_PATH
            or body["origin_request_authority_id"]
            != _final_authority.RECOVERY_REQUEST_AUTHORITY_ID
            or body["origin_run_request_relative_path"]
            != PHOBERT_RELEASE_ORIGIN_REQUEST_RELATIVE_PATH
        ):
            raise PhoBertReleaseError("release upstream authority paths drifted")
        for field in (
            "final_comparison_authority_sha256",
            "origin_run_request_sha256",
            "origin_control_template_sha256",
            "origin_transfer_authority_sha256",
        ):
            _require_sha256(body[field], field.replace("_", " "))

    def _validate_run(self) -> None:
        body = _require_exact_keys(
            self.run,
            frozenset(
                {
                    "evidence_relative_path",
                    "evidence_sha256",
                    "run_id",
                    "status",
                    "selected_optimizer_step",
                    "global_optimizer_step",
                    "resolved_config_relative_path",
                    "resolved_config_sha256",
                    "trainer_state_relative_path",
                    "trainer_state_sha256",
                }
            ),
            "release run authority",
        )
        if body["evidence_relative_path"] != PHOBERT_RELEASE_RUN_EVIDENCE_NAME:
            raise PhoBertReleaseError("release run evidence path drifted")
        if (
            body["resolved_config_relative_path"]
            != PHOBERT_RELEASE_RESOLVED_CONFIG_NAME
        ):
            raise PhoBertReleaseError("release resolved-config path drifted")
        if body["trainer_state_relative_path"] != PHOBERT_RELEASE_TRAINER_STATE_NAME:
            raise PhoBertReleaseError("release trainer-state path drifted")
        _require_sha256(body["evidence_sha256"], "run evidence sha256")
        _require_sha256(body["resolved_config_sha256"], "resolved-config sha256")
        _require_sha256(body["trainer_state_sha256"], "trainer-state sha256")
        if body["run_id"] != _final_authority.RECOVERY_PHOBERT_RUN_ID:
            raise PhoBertReleaseError("release run is not the fixed PhoBERT v12 run")
        if body["status"] != "complete":
            raise PhoBertReleaseError("release run is not complete")
        selected = _require_nonnegative_int(
            body["selected_optimizer_step"], "selected optimizer step"
        )
        global_step = _require_nonnegative_int(
            body["global_optimizer_step"], "global optimizer step"
        )
        if selected > global_step:
            raise PhoBertReleaseError("selected optimizer step exceeds global step")

    def _validate_selected_model(self) -> None:
        body = _require_exact_keys(
            self.selected_model,
            frozenset(
                {
                    "artifact_logical_name",
                    "artifact_role",
                    "artifact_kind",
                    "source_relative_path",
                    "bundle_relative_path",
                    "artifact_sha256",
                    "checkpoint_identity",
                }
            ),
            "selected model authority",
        )
        expected = {
            "artifact_logical_name": "model-artifact",
            "artifact_role": "model_artifact",
            "artifact_kind": "directory",
            "source_relative_path": "adapter-or-model",
            "bundle_relative_path": PHOBERT_RELEASE_MODEL_ROOT,
        }
        if any(body[key] != value for key, value in expected.items()):
            raise PhoBertReleaseError("selected model artifact contract drifted")
        _require_sha256(body["artifact_sha256"], "selected artifact sha256")
        identity = body["checkpoint_identity"]
        if not isinstance(identity, str) or not _CHECKPOINT_ID_RE.fullmatch(identity):
            raise PhoBertReleaseError("selected checkpoint identity is invalid")

    def _validate_base_model(self) -> None:
        body = _require_exact_keys(
            self.base_model,
            frozenset(
                {
                    "provenance_relative_path",
                    "provenance_sha256",
                    "model_id",
                    "model_revision",
                    "local_path_sha256",
                    "snapshot_sha256",
                    "file_count",
                    "total_bytes",
                }
            ),
            "base model authority",
        )
        expected_path = f"{PHOBERT_RELEASE_MODEL_ROOT}/{PHOBERT_BASE_MODEL_MANIFEST_NAME}"
        if body["provenance_relative_path"] != expected_path:
            raise PhoBertReleaseError("base provenance path drifted")
        if body["model_id"] != self.model_id or body["model_revision"] != self.model_revision:
            raise PhoBertReleaseError("base provenance model identity drifted")
        for key in ("provenance_sha256", "local_path_sha256", "snapshot_sha256"):
            _require_sha256(body[key], key.replace("_", " "))
        _require_positive_int(body["file_count"], "base snapshot file count")
        _require_positive_int(body["total_bytes"], "base snapshot total bytes")

    def _body_without_hash(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "role": self.role,
            "model_id": self.model_id,
            "model_revision": self.model_revision,
            "preprocessor_sha256": self.preprocessor_sha256,
            "upstream": dict(self.upstream),
            "run": dict(self.run),
            "selected_model": dict(self.selected_model),
            "base_model": dict(self.base_model),
            "model_tree": self.model_tree.as_dict(),
            "tokenizer_tree": self.tokenizer_tree.as_dict(),
        }

    def as_dict(self) -> dict[str, object]:
        body = self._body_without_hash()
        body["authority_sha256"] = self.authority_sha256
        return body

    @classmethod
    def from_dict(cls, value: object) -> "PhoBertReleaseManifest":
        body = _require_exact_keys(
            value,
            frozenset(
                {
                    "schema_version",
                    "role",
                    "model_id",
                    "model_revision",
                    "preprocessor_sha256",
                    "upstream",
                    "run",
                    "selected_model",
                    "base_model",
                    "model_tree",
                    "tokenizer_tree",
                    "authority_sha256",
                }
            ),
            "PhoBERT release manifest",
        )
        upstream = body["upstream"]
        run = body["run"]
        selected = body["selected_model"]
        base = body["base_model"]
        if (
            not isinstance(upstream, dict)
            or not isinstance(run, dict)
            or not isinstance(selected, dict)
            or not isinstance(base, dict)
        ):
            raise PhoBertReleaseError("PhoBERT release nested authorities are malformed")
        return cls(
            upstream=dict(upstream),
            run=dict(run),
            selected_model=dict(selected),
            base_model=dict(base),
            model_tree=ReleaseTreeAuthority.from_dict(body["model_tree"]),
            tokenizer_tree=ReleaseTreeAuthority.from_dict(body["tokenizer_tree"]),
            model_id=body["model_id"],  # type: ignore[arg-type]
            model_revision=body["model_revision"],  # type: ignore[arg-type]
            preprocessor_sha256=body["preprocessor_sha256"],  # type: ignore[arg-type]
            authority_sha256=body["authority_sha256"],  # type: ignore[arg-type]
            schema_version=body["schema_version"],  # type: ignore[arg-type]
            role=body["role"],  # type: ignore[arg-type]
        )


@dataclass(frozen=True, slots=True)
class PhoBertReleaseReceipt:
    upstream: Mapping[str, object]
    bundle_manifest_sha256: str
    bundle_manifest_authority_sha256: str
    bundle_root_sha256: str
    selected_run_id: str
    selected_artifact_sha256: str
    tokenizer_sha256: str
    run_evidence_sha256: str
    resolved_config_sha256: str
    selected_checkpoint_identity: str
    base_provenance_sha256: str
    base_snapshot_sha256: str
    preprocessor_sha256: str
    authority_sha256: str
    schema_version: str = PHOBERT_RELEASE_RECEIPT_SCHEMA_VERSION
    role: str = "phobert"
    bundle_relative_path: str = PHOBERT_RELEASE_BUNDLE_RELATIVE_PATH
    bundle_manifest_relative_path: str = (
        f"{PHOBERT_RELEASE_BUNDLE_RELATIVE_PATH}/{PHOBERT_RELEASE_MANIFEST_NAME}"
    )
    model_artifact_relative_path: str = (
        f"{PHOBERT_RELEASE_BUNDLE_RELATIVE_PATH}/{PHOBERT_RELEASE_MODEL_ROOT}"
    )
    tokenizer_relative_path: str = (
        f"{PHOBERT_RELEASE_BUNDLE_RELATIVE_PATH}/{PHOBERT_RELEASE_TOKENIZER_ROOT}"
    )

    def __post_init__(self) -> None:
        if (
            self.schema_version != PHOBERT_RELEASE_RECEIPT_SCHEMA_VERSION
            or self.role != "phobert"
            or self.bundle_relative_path != PHOBERT_RELEASE_BUNDLE_RELATIVE_PATH
            or self.bundle_manifest_relative_path
            != f"{PHOBERT_RELEASE_BUNDLE_RELATIVE_PATH}/{PHOBERT_RELEASE_MANIFEST_NAME}"
            or self.model_artifact_relative_path
            != f"{PHOBERT_RELEASE_BUNDLE_RELATIVE_PATH}/{PHOBERT_RELEASE_MODEL_ROOT}"
            or self.tokenizer_relative_path
            != f"{PHOBERT_RELEASE_BUNDLE_RELATIVE_PATH}/{PHOBERT_RELEASE_TOKENIZER_ROOT}"
        ):
            raise PhoBertReleaseError("PhoBERT release receipt layout drifted")
        upstream = _require_exact_keys(
            self.upstream,
            frozenset(
                {
                    "final_comparison_authority_relative_path",
                    "final_comparison_authority_sha256",
                    "origin_request_authority_id",
                    "origin_run_request_relative_path",
                    "origin_run_request_sha256",
                    "origin_control_template_sha256",
                    "origin_transfer_authority_sha256",
                }
            ),
            "receipt upstream authority",
        )
        if (
            upstream["final_comparison_authority_relative_path"]
            != _final_authority.FIXED_FINAL_COMPARISON_AUTHORITY_PATH
            or upstream["origin_request_authority_id"]
            != _final_authority.RECOVERY_REQUEST_AUTHORITY_ID
            or upstream["origin_run_request_relative_path"]
            != PHOBERT_RELEASE_ORIGIN_REQUEST_RELATIVE_PATH
        ):
            raise PhoBertReleaseError("receipt upstream authority paths drifted")
        for field in (
            "final_comparison_authority_sha256",
            "origin_run_request_sha256",
            "origin_control_template_sha256",
            "origin_transfer_authority_sha256",
        ):
            _require_sha256(upstream[field], f"receipt {field.replace('_', ' ')}")
        if self.selected_run_id != _final_authority.RECOVERY_PHOBERT_RUN_ID:
            raise PhoBertReleaseError("receipt does not select the fixed PhoBERT v12 run")
        for name, value in (
            ("bundle manifest", self.bundle_manifest_sha256),
            ("bundle manifest authority", self.bundle_manifest_authority_sha256),
            ("bundle root", self.bundle_root_sha256),
            ("selected artifact", self.selected_artifact_sha256),
            ("tokenizer", self.tokenizer_sha256),
            ("run evidence", self.run_evidence_sha256),
            ("resolved config", self.resolved_config_sha256),
            ("base provenance", self.base_provenance_sha256),
            ("base snapshot", self.base_snapshot_sha256),
            ("preprocessor", self.preprocessor_sha256),
        ):
            _require_sha256(value, f"receipt {name} sha256")
        if not _CHECKPOINT_ID_RE.fullmatch(self.selected_checkpoint_identity):
            raise PhoBertReleaseError("receipt selected checkpoint identity is invalid")
        if self.authority_sha256 != _sha256(
            canonical_json_bytes(self._body_without_hash())
        ):
            raise PhoBertReleaseError("PhoBERT release receipt self-hash mismatch")
        _reject_absolute_path_leakage(self._body_without_hash(), "release receipt")
        object.__setattr__(self, "upstream", MappingProxyType(dict(self.upstream)))

    def _body_without_hash(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "role": self.role,
            "bundle_relative_path": self.bundle_relative_path,
            "bundle_manifest_relative_path": self.bundle_manifest_relative_path,
            "model_artifact_relative_path": self.model_artifact_relative_path,
            "tokenizer_relative_path": self.tokenizer_relative_path,
            "upstream": dict(self.upstream),
            "bundle_manifest_sha256": self.bundle_manifest_sha256,
            "bundle_manifest_authority_sha256": (
                self.bundle_manifest_authority_sha256
            ),
            "bundle_root_sha256": self.bundle_root_sha256,
            "selected_run_id": self.selected_run_id,
            "selected_artifact_sha256": self.selected_artifact_sha256,
            "tokenizer_sha256": self.tokenizer_sha256,
            "run_evidence_sha256": self.run_evidence_sha256,
            "resolved_config_sha256": self.resolved_config_sha256,
            "selected_checkpoint_identity": self.selected_checkpoint_identity,
            "base_provenance_sha256": self.base_provenance_sha256,
            "base_snapshot_sha256": self.base_snapshot_sha256,
            "preprocessor_sha256": self.preprocessor_sha256,
        }

    def as_dict(self) -> dict[str, object]:
        body = self._body_without_hash()
        body["authority_sha256"] = self.authority_sha256
        return body

    @classmethod
    def from_dict(cls, value: object) -> "PhoBertReleaseReceipt":
        body = _require_exact_keys(
            value,
            frozenset(
                {
                    "schema_version",
                    "role",
                    "bundle_relative_path",
                    "bundle_manifest_relative_path",
                    "model_artifact_relative_path",
                    "tokenizer_relative_path",
                    "upstream",
                    "bundle_manifest_sha256",
                    "bundle_manifest_authority_sha256",
                    "bundle_root_sha256",
                    "selected_run_id",
                    "selected_artifact_sha256",
                    "tokenizer_sha256",
                    "run_evidence_sha256",
                    "resolved_config_sha256",
                    "selected_checkpoint_identity",
                    "base_provenance_sha256",
                    "base_snapshot_sha256",
                    "preprocessor_sha256",
                    "authority_sha256",
                }
            ),
            "PhoBERT release receipt",
        )
        return cls(**body)  # type: ignore[arg-type]


@dataclass(frozen=True, slots=True)
class _VerifiedBundleState:
    root: Path
    manifest: PhoBertReleaseManifest
    manifest_sha256: str
    bundle_root_sha256: str
    evidence: RunEvidence
    controlled_config: ResumeControlledConfig

    def __post_init__(self) -> None:
        if not self.root.is_absolute():
            raise PhoBertReleaseError("verified bundle root must be absolute")
        _require_sha256(self.manifest_sha256, "release manifest sha256")
        _require_sha256(self.bundle_root_sha256, "release bundle root sha256")


@dataclass(frozen=True, slots=True)
class VerifiedPhoBertReleaseBundle:
    root: Path
    manifest: PhoBertReleaseManifest
    manifest_sha256: str
    bundle_root_sha256: str
    receipt_path: Path
    receipt: PhoBertReleaseReceipt
    receipt_sha256: str

    def __post_init__(self) -> None:
        if not self.root.is_absolute() or not self.receipt_path.is_absolute():
            raise PhoBertReleaseError("verified release paths must be absolute")
        _require_sha256(self.manifest_sha256, "release manifest sha256")
        _require_sha256(self.bundle_root_sha256, "release bundle root sha256")
        _require_sha256(self.receipt_sha256, "release receipt sha256")


class _WindowsPathLease:
    """Retain one path and every ancestor under non-delete-shared handles."""

    __slots__ = (
        "path",
        "description",
        "expected_directory",
        "_closed",
        "_handles",
        "_info_type",
        "_kernel32",
        "_leaf_identity",
    )

    def __init__(
        self,
        path: Path,
        description: str,
        *,
        expected_directory: bool,
        deny_write: bool,
        allow_leaf_delete: bool = False,
    ) -> None:
        if os.name != "nt":
            raise PhoBertReleaseError(
                "PhoBERT release capture requires Windows handle enforcement"
            )
        self.path = Path(path)
        self.description = description
        self.expected_directory = expected_directory
        self._closed = False
        self._handles: list[tuple[object, bool, tuple[int, int, int]]] = []
        self._info_type = None
        self._kernel32 = None
        self._leaf_identity: tuple[int, int, int] | None = None
        try:
            self._configure_api()
            ancestors = self.path.parents if not expected_directory else self.path.parents
            for ancestor in reversed(tuple(ancestors)):
                self._hold_path(
                    ancestor,
                    expected_directory=True,
                    deny_write=False,
                    allow_delete=False,
                )
            self._leaf_identity = self._hold_path(
                self.path,
                expected_directory=expected_directory,
                deny_write=deny_write,
                allow_delete=allow_leaf_delete,
            )
            self.assert_intact()
        except BaseException:
            self.close()
            raise

    @property
    def leaf_identity(self) -> tuple[int, int, int]:
        if self._leaf_identity is None:
            raise PhoBertReleaseError(f"{self.description} lease is closed")
        return self._leaf_identity

    def _configure_api(self) -> None:
        import ctypes
        from ctypes import wintypes

        class FileTime(ctypes.Structure):
            _fields_ = [
                ("dwLowDateTime", wintypes.DWORD),
                ("dwHighDateTime", wintypes.DWORD),
            ]

        class ByHandleFileInformation(ctypes.Structure):
            _fields_ = [
                ("dwFileAttributes", wintypes.DWORD),
                ("ftCreationTime", FileTime),
                ("ftLastAccessTime", FileTime),
                ("ftLastWriteTime", FileTime),
                ("dwVolumeSerialNumber", wintypes.DWORD),
                ("nFileSizeHigh", wintypes.DWORD),
                ("nFileSizeLow", wintypes.DWORD),
                ("nNumberOfLinks", wintypes.DWORD),
                ("nFileIndexHigh", wintypes.DWORD),
                ("nFileIndexLow", wintypes.DWORD),
            ]

        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.CreateFileW.argtypes = [
            wintypes.LPCWSTR,
            wintypes.DWORD,
            wintypes.DWORD,
            wintypes.LPVOID,
            wintypes.DWORD,
            wintypes.DWORD,
            wintypes.HANDLE,
        ]
        kernel32.CreateFileW.restype = wintypes.HANDLE
        kernel32.GetFileInformationByHandle.argtypes = [
            wintypes.HANDLE,
            ctypes.POINTER(ByHandleFileInformation),
        ]
        kernel32.GetFileInformationByHandle.restype = wintypes.BOOL
        kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
        kernel32.CloseHandle.restype = wintypes.BOOL
        self._kernel32 = kernel32
        self._info_type = ByHandleFileInformation

    def _inspect_handle(
        self,
        handle: object,
        *,
        expected_directory: bool,
    ) -> tuple[int, int, int]:
        import ctypes

        if self._kernel32 is None or self._info_type is None:
            raise PhoBertReleaseError(f"{self.description} Windows API is unavailable")
        information = self._info_type()
        if not self._kernel32.GetFileInformationByHandle(
            handle,
            ctypes.byref(information),
        ):
            code = ctypes.get_last_error()
            raise PhoBertReleaseError(
                f"{self.description} held path cannot be inspected: winerror={code}"
            )
        attributes = int(information.dwFileAttributes)
        is_directory = bool(attributes & 0x00000010)
        if attributes & 0x00000400 or is_directory is not expected_directory:
            raise PhoBertReleaseError(
                f"{self.description} held path is redirecting or type-drifted"
            )
        return (
            int(information.dwVolumeSerialNumber),
            int(information.nFileIndexHigh),
            int(information.nFileIndexLow),
        )

    def _hold_path(
        self,
        target: Path,
        *,
        expected_directory: bool,
        deny_write: bool,
        allow_delete: bool,
    ) -> tuple[int, int, int]:
        import ctypes

        if self._kernel32 is None:
            raise PhoBertReleaseError(f"{self.description} Windows API is unavailable")
        invalid = ctypes.c_void_p(-1).value
        share_mode = 0x00000001 if deny_write else 0x00000003
        if allow_delete:
            share_mode |= 0x00000004
        handle = self._kernel32.CreateFileW(
            str(target),
            0x80000000,
            share_mode,
            None,
            3,
            0x00200000 | 0x02000000,
            None,
        )
        if handle == invalid:
            code = ctypes.get_last_error()
            raise PhoBertReleaseError(
                f"{self.description} is missing or unsafe and cannot be locked: "
                f"winerror={code}"
            )
        try:
            identity = self._inspect_handle(
                handle,
                expected_directory=expected_directory,
            )
        except BaseException:
            self._kernel32.CloseHandle(handle)
            raise
        self._handles.append((handle, expected_directory, identity))
        return identity

    def assert_intact(self) -> None:
        if self._closed or not self._handles or self._leaf_identity is None:
            raise PhoBertReleaseError(f"{self.description} path lease is closed")
        for handle, expected_directory, identity in self._handles:
            if self._inspect_handle(handle, expected_directory=expected_directory) != identity:
                raise PhoBertReleaseError(f"{self.description} held identity drifted")

    def same_object_at(self, candidate: Path) -> bool:
        """Compare a current pathname to the retained leaf object identity."""

        self.assert_intact()
        temporary = _WindowsPathLease(
            candidate,
            f"{self.description} identity comparison",
            expected_directory=self.expected_directory,
            deny_write=False,
            allow_leaf_delete=True,
        )
        try:
            return temporary.leaf_identity == self.leaf_identity
        finally:
            temporary.close()

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        self._leaf_identity = None
        if self._kernel32 is not None:
            while self._handles:
                handle, _, _ = self._handles.pop()
                self._kernel32.CloseHandle(handle)

    def __enter__(self) -> "_WindowsPathLease":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()


def _require_path_absent_no_follow(path: Path, description: str) -> None:
    """Prove a leaf is absent without resolving a redirecting leaf or ancestor."""

    if os.name != "nt":
        raise PhoBertReleaseError(
            "PhoBERT release publication requires Windows handle enforcement"
        )
    import ctypes
    from ctypes import wintypes

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.CreateFileW.argtypes = [
        wintypes.LPCWSTR,
        wintypes.DWORD,
        wintypes.DWORD,
        wintypes.LPVOID,
        wintypes.DWORD,
        wintypes.DWORD,
        wintypes.HANDLE,
    ]
    kernel32.CreateFileW.restype = wintypes.HANDLE
    kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel32.CloseHandle.restype = wintypes.BOOL
    invalid = ctypes.c_void_p(-1).value
    handle = kernel32.CreateFileW(
        str(path),
        0x00000080,
        0x00000001 | 0x00000002 | 0x00000004,
        None,
        3,
        0x00200000 | 0x02000000,
        None,
    )
    if handle != invalid:
        kernel32.CloseHandle(handle)
        raise PhoBertReleaseError(f"{description} already exists")
    code = ctypes.get_last_error()
    if code != 2:
        raise PhoBertReleaseError(
            f"{description} absence could not be proven safely: winerror={code}"
        )


def _tree_authority_from_lease(
    lease: _WindowsClosedTreeLease,
    relative_root: str,
) -> ReleaseTreeAuthority:
    lease.assert_intact()
    directories = tuple(
        relative
        for relative, kind, _, _ in lease.inventory
        if kind == "directory"
    )
    files = tuple(
        ReleaseFileRecord(relative, byte_count, digest)
        for relative, kind, byte_count, digest in lease.inventory
        if kind == "file"
    )
    content_sha256 = build_model_checksum(lease.root)
    lease.assert_intact()
    return ReleaseTreeAuthority(
        relative_root=relative_root,
        directories=directories,
        files=files,
        tree_sha256=_tree_sha256(directories, files),
        content_sha256=content_sha256,
    )


def _reject_tree_path_leakage(
    root: Path,
    authority: ReleaseTreeAuthority,
    lease: _WindowsClosedTreeLease,
    description: str,
) -> None:
    """Reject portable metadata containing host-specific absolute paths."""

    lease.assert_intact()
    for record in authority.files:
        path = root / PurePosixPath(record.relative_path)
        relative = PurePosixPath(record.relative_path)
        suffix = relative.suffix.lower()
        name = relative.name.lower()
        is_lexical_asset = (
            name in _LEXICAL_ASSET_NAMES
            or suffix in _LEXICAL_ASSET_SUFFIXES
            or name.startswith(("vocab.", "merges.", "dict.", "dictionary."))
        )
        is_textual_metadata = suffix in (
            _PORTABLE_JSON_SUFFIXES
            | _PORTABLE_JSONL_SUFFIXES
            | _PORTABLE_TEXT_SUFFIXES
        )
        if (
            is_lexical_asset
            or suffix in _OPAQUE_BINARY_SUFFIXES
            or (suffix != _SAFETENSORS_SUFFIX and not is_textual_metadata)
        ):
            lease.assert_intact()
            continue
        try:
            if suffix == _SAFETENSORS_SUFFIX:
                with path.open("rb") as handle:
                    prefix = handle.read(8)
                    if len(prefix) != 8:
                        lease.assert_intact()
                        continue
                    header_bytes = int.from_bytes(prefix, "little", signed=False)
                    if header_bytes <= 0 or header_bytes > record.bytes - 8:
                        lease.assert_intact()
                        continue
                    if header_bytes > _MAX_SAFETENSORS_HEADER_BYTES:
                        raise PhoBertReleaseError(
                            f"{description} safetensors header exceeds safety bound"
                        )
                    header = handle.read(header_bytes)
                    if len(header) != header_bytes:
                        raise PhoBertReleaseError(
                            f"{description} safetensors header was truncated"
                        )
                if header.lstrip().startswith(b"{"):
                    _reject_portable_payload_path_leakage(
                        header,
                        description,
                        relative_path=f"{record.relative_path}.json",
                    )
            else:
                _reject_portable_payload_path_leakage(
                    path.read_bytes(),
                    description,
                    lexical_subtree_patterns=(
                        _TOKENIZER_LEXICAL_SUBTREE_PATTERNS.get(name, ())
                    ),
                    relative_path=record.relative_path,
                )
        except OSError as exc:
            raise PhoBertReleaseError(
                f"{description} could not be scanned for path leakage"
            ) from exc
        lease.assert_intact()


def _write_exact_file(path: Path, payload: bytes) -> None:
    try:
        with path.open("xb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
    except OSError as exc:
        raise PhoBertReleaseError(f"release file could not be written: {path.name}") from exc
    try:
        if path.read_bytes() != payload:
            raise PhoBertReleaseError(f"release file read-back drifted: {path.name}")
    except OSError as exc:
        raise PhoBertReleaseError(f"release file could not be read back: {path.name}") from exc


def _copy_tree_from_authority(
    source_root: Path,
    destination_root: Path,
    authority: ReleaseTreeAuthority,
    source_lease: _WindowsClosedTreeLease,
) -> None:
    try:
        destination_root.mkdir()
        for relative in sorted(
            authority.directories,
            key=lambda value: (len(PurePosixPath(value).parts), value),
        ):
            (destination_root / PurePosixPath(relative)).mkdir()
        for record in authority.files:
            source_lease.assert_intact()
            source = source_root / PurePosixPath(record.relative_path)
            destination = destination_root / PurePosixPath(record.relative_path)
            digest = hashlib.sha256()
            byte_count = 0
            with source.open("rb") as source_handle, destination.open("xb") as output_handle:
                while chunk := source_handle.read(1024 * 1024):
                    digest.update(chunk)
                    byte_count += len(chunk)
                    output_handle.write(chunk)
                output_handle.flush()
                os.fsync(output_handle.fileno())
            if (byte_count, digest.hexdigest()) != (record.bytes, record.sha256):
                raise PhoBertReleaseError(
                    f"source tree changed while copying {record.relative_path}"
                )
            if destination.stat().st_size != record.bytes:
                raise PhoBertReleaseError(
                    f"release copy size drifted for {record.relative_path}"
                )
        source_lease.assert_intact()
    except PhoBertReleaseError:
        raise
    except OSError as exc:
        raise PhoBertReleaseError("release tree could not be copied safely") from exc


def _validate_tokenizer_authority(authority: ReleaseTreeAuthority) -> None:
    records = {item.relative_path: item for item in authority.files}
    config = records.get("tokenizer_config.json")
    if config is None or config.bytes == 0:
        raise PhoBertReleaseError("PhoBERT tokenizer lacks tokenizer_config.json")
    vocabulary_names = {
        "tokenizer.json",
        "vocab.txt",
        "sentencepiece.bpe.model",
    }
    if not any(name in records and records[name].bytes > 0 for name in vocabulary_names):
        raise PhoBertReleaseError("PhoBERT tokenizer lacks a non-empty vocabulary asset")


def _artifact_by_role(evidence: RunEvidence, role: str) -> object:
    matches = tuple(item for item in evidence.artifacts if item.role == role)
    if len(matches) != 1:
        raise PhoBertReleaseError(f"run evidence requires exactly one {role} artifact")
    return matches[0]


@dataclass(frozen=True, slots=True)
class _UpstreamAuthorities:
    final_authority_path: Path
    origin_request_path: Path
    final_authority_sha256: str
    origin_request_sha256: str
    control_template_sha256: str
    transfer_authority_sha256: str

    def as_dict(self) -> dict[str, object]:
        return {
            "final_comparison_authority_relative_path": (
                _final_authority.FIXED_FINAL_COMPARISON_AUTHORITY_PATH
            ),
            "final_comparison_authority_sha256": self.final_authority_sha256,
            "origin_request_authority_id": (
                _final_authority.RECOVERY_REQUEST_AUTHORITY_ID
            ),
            "origin_run_request_relative_path": (
                PHOBERT_RELEASE_ORIGIN_REQUEST_RELATIVE_PATH
            ),
            "origin_run_request_sha256": self.origin_request_sha256,
            "origin_control_template_sha256": self.control_template_sha256,
            "origin_transfer_authority_sha256": self.transfer_authority_sha256,
        }


def _upstream_paths(repository: Path) -> tuple[Path, Path]:
    final_authority_path = _lexical_absolute(
        repository
        / PurePosixPath(_final_authority.FIXED_FINAL_COMPARISON_AUTHORITY_PATH),
        "final Phase40 comparison authority",
    )
    origin_request_path = _lexical_absolute(
        repository / PurePosixPath(PHOBERT_RELEASE_ORIGIN_REQUEST_RELATIVE_PATH),
        "PhoBERT v12 origin run request",
    )
    return final_authority_path, origin_request_path


def _authority_object_sha256(value: object) -> str:
    if hasattr(value, "model_dump"):
        value = value.model_dump(mode="json")
    return _sha256(canonical_json_bytes(value))


def _load_verified_upstream_authorities(
    repository: Path,
    evidence: RunEvidence | None,
    controlled_config: ResumeControlledConfig | None = None,
) -> _UpstreamAuthorities:
    final_authority_path, origin_request_path = _upstream_paths(repository)
    _, final_authority_payload = _load_canonical_json(
        final_authority_path,
        "final Phase40 comparison authority",
    )
    _, origin_request_payload = _load_canonical_json(
        origin_request_path,
        "PhoBERT v12 origin run request",
    )
    try:
        verified = _final_authority.load_frozen_phase40_final_comparison_authority(
            repo_root=repository
        )
    except Exception as exc:
        raise PhoBertReleaseError(
            "fixed final Phase40 comparison authority is invalid"
        ) from exc
    resolution = verified.by_run_id.get(
        _final_authority.RECOVERY_PHOBERT_RUN_ID
    )
    if resolution is None:
        raise PhoBertReleaseError(
            "final comparison authority does not resolve PhoBERT v12"
        )
    origin = resolution.origin
    requested = resolution.requested_run
    expected_identity = (
        _final_authority.RECOVERY_PHOBERT_RUN_ID,
        ModelFamily.PHOBERT,
        AdaptationMode.CLASSIFICATION_HEAD,
        RunKind.FULL.value,
        _final_authority.PHOBERT_RETURNED_ROOT,
        0,
        None,
    )
    actual_identity = (
        resolution.run_id,
        requested.model_family,
        requested.adaptation_mode,
        requested.run_kind,
        requested.returned_root,
        requested.step_origin,
        requested.probe_parent,
    )
    if actual_identity != expected_identity:
        raise PhoBertReleaseError(
            "final comparison authority resolved a non-canonical PhoBERT v12 identity"
        )
    if (
        origin.authority_id != _final_authority.RECOVERY_REQUEST_AUTHORITY_ID
        or origin.root_policy != "fixed_phobert_v12_capsule"
    ):
        raise PhoBertReleaseError(
            "final comparison authority resolves PhoBERT from the wrong origin request"
        )
    request = resolution.origin_request
    matching_runs = tuple(
        item
        for item in request.runs
        if item.run_id == _final_authority.RECOVERY_PHOBERT_RUN_ID
    )
    if matching_runs != (requested,):
        raise PhoBertReleaseError(
            "resolved PhoBERT v12 run is not exact in its origin request"
        )
    origin_request_sha256 = _authority_object_sha256(request)
    if (
        origin.request_sha256 != origin_request_sha256
        or _sha256(origin_request_payload) != origin_request_sha256
        or origin_request_payload
        != canonical_json_bytes(request.model_dump(mode="json"))
    ):
        raise PhoBertReleaseError(
            "resolved PhoBERT origin request differs from its bound SHA-256"
        )
    template = resolution.control_template
    if (
        request.control_template_by_run.get(_final_authority.RECOVERY_PHOBERT_RUN_ID)
        != template
        or request.control_template_digest_by_run.get(
            _final_authority.RECOVERY_PHOBERT_RUN_ID
        )
        != template.sha256
    ):
        raise PhoBertReleaseError(
            "resolved PhoBERT v12 control template is not exact in its origin request"
        )
    template_config = template.materialize_for_validation()
    if (
        template_config.experiment_identity.model_family != ModelFamily.PHOBERT
        or template_config.experiment_identity.adaptation_mode
        != AdaptationMode.CLASSIFICATION_HEAD
        or template_config.experiment_identity.run_kind != RunKind.FULL
        or template_config.model_id != PHOBERT_MODEL_ID
        or template_config.model_revision != PHOBERT_MODEL_REVISION
    ):
        raise PhoBertReleaseError(
            "resolved PhoBERT v12 control template has the wrong model identity"
        )
    derived_transfer = transfer_authority_from_request(request)
    if resolution.transfer_authority != derived_transfer:
        raise PhoBertReleaseError(
            "resolved PhoBERT v12 transfer authority is not request-derived"
        )
    if evidence is not None and (
        evidence.run_id != _final_authority.RECOVERY_PHOBERT_RUN_ID
        or evidence.transfer_authority is None
        or evidence.transfer_authority != derived_transfer
    ):
        raise PhoBertReleaseError(
            "PhoBERT run evidence differs from its v12 recovery origin"
        )
    if (evidence is None) != (controlled_config is None):
        raise PhoBertReleaseError(
            "run evidence and resolved config must be verified together"
        )
    if controlled_config is not None:
        try:
            template.verify_runtime_config(controlled_config)
        except RuntimeError as exc:
            raise PhoBertReleaseError(
                "PhoBERT resolved config differs from its v12 control template"
            ) from exc
    if _sha256(final_authority_payload) != verified.authority_sha256:
        raise PhoBertReleaseError(
            "resolved final comparison authority differs from its fixed bytes"
        )
    return _UpstreamAuthorities(
        final_authority_path=final_authority_path,
        origin_request_path=origin_request_path,
        final_authority_sha256=verified.authority_sha256,
        origin_request_sha256=origin_request_sha256,
        control_template_sha256=template.sha256,
        transfer_authority_sha256=_authority_object_sha256(derived_transfer),
    )


def _validate_finalized_phobert_run(
    evidence: RunEvidence,
) -> tuple[object, object, object]:
    if (
        evidence.status != EvidenceStatus.COMPLETE
        or not evidence.comparison_eligible
        or evidence.run_id != _final_authority.RECOVERY_PHOBERT_RUN_ID
        or evidence.run_kind != RunKind.FULL
        or evidence.experiment_identity.model_family != ModelFamily.PHOBERT
        or evidence.experiment_identity.adaptation_mode
        != AdaptationMode.CLASSIFICATION_HEAD
        or evidence.model_id != PHOBERT_MODEL_ID
        or evidence.model_revision != PHOBERT_MODEL_REVISION
    ):
        raise PhoBertReleaseError(
            "release requires one complete comparison-eligible PhoBERT full run"
        )
    selected = evidence.selected_checkpoint
    if selected is None or not selected.safety_gate_passed:
        raise PhoBertReleaseError("release requires a safety-passing selected checkpoint")
    if not _CHECKPOINT_ID_RE.fullmatch(selected.artifact_identity):
        raise PhoBertReleaseError("selected PhoBERT checkpoint identity is malformed")
    model_artifact = _artifact_by_role(evidence, "model_artifact")
    trainer_artifact = _artifact_by_role(evidence, "trainer_state")
    resolved_config_artifact = _artifact_by_role(evidence, "resolved_config")
    if (
        model_artifact.logical_name != "model-artifact"
        or model_artifact.relative_path != "adapter-or-model"
        or model_artifact.kind != "directory"
    ):
        raise PhoBertReleaseError("finalized model artifact row is not canonical")
    if (
        trainer_artifact.logical_name != "trainer-state"
        or trainer_artifact.relative_path != "trainer_state.json"
        or trainer_artifact.kind != "file"
    ):
        raise PhoBertReleaseError("finalized trainer-state artifact row is not canonical")
    if (
        resolved_config_artifact.logical_name != "resolved-config"
        or resolved_config_artifact.relative_path != PHOBERT_RELEASE_RESOLVED_CONFIG_NAME
        or resolved_config_artifact.kind != "file"
        or resolved_config_artifact.sha256 != evidence.resolved_config_sha256
    ):
        raise PhoBertReleaseError("finalized resolved-config artifact row is not canonical")
    return model_artifact, trainer_artifact, resolved_config_artifact


def _manifest_for_sources(
    *,
    upstream: _UpstreamAuthorities,
    evidence: RunEvidence,
    evidence_payload: bytes,
    resolved_config_payload: bytes,
    trainer_payload: bytes,
    global_step: int,
    model_artifact: object,
    base: PhoBertBaseModelProvenance,
    base_payload: bytes,
    model_tree: ReleaseTreeAuthority,
    tokenizer_tree: ReleaseTreeAuthority,
) -> PhoBertReleaseManifest:
    selected = evidence.selected_checkpoint
    if selected is None:  # validated by _validate_finalized_phobert_run
        raise PhoBertReleaseError("selected checkpoint disappeared")
    body = {
        "schema_version": PHOBERT_RELEASE_SCHEMA_VERSION,
        "role": "phobert",
        "model_id": evidence.model_id,
        "model_revision": evidence.model_revision,
        "preprocessor_sha256": evidence.prompt_or_preprocessor_sha256,
        "upstream": upstream.as_dict(),
        "run": {
            "evidence_relative_path": PHOBERT_RELEASE_RUN_EVIDENCE_NAME,
            "evidence_sha256": _sha256(evidence_payload),
            "run_id": evidence.run_id,
            "status": "complete",
            "selected_optimizer_step": selected.optimizer_step,
            "global_optimizer_step": global_step,
            "resolved_config_relative_path": PHOBERT_RELEASE_RESOLVED_CONFIG_NAME,
            "resolved_config_sha256": _sha256(resolved_config_payload),
            "trainer_state_relative_path": PHOBERT_RELEASE_TRAINER_STATE_NAME,
            "trainer_state_sha256": _sha256(trainer_payload),
        },
        "selected_model": {
            "artifact_logical_name": model_artifact.logical_name,
            "artifact_role": model_artifact.role,
            "artifact_kind": model_artifact.kind,
            "source_relative_path": model_artifact.relative_path,
            "bundle_relative_path": PHOBERT_RELEASE_MODEL_ROOT,
            "artifact_sha256": model_artifact.sha256,
            "checkpoint_identity": selected.artifact_identity,
        },
        "base_model": {
            "provenance_relative_path": (
                f"{PHOBERT_RELEASE_MODEL_ROOT}/{PHOBERT_BASE_MODEL_MANIFEST_NAME}"
            ),
            "provenance_sha256": _sha256(base_payload),
            "model_id": base.model_id,
            "model_revision": base.model_revision,
            "local_path_sha256": base.local_path_sha256,
            "snapshot_sha256": base.content_sha256,
            "file_count": base.file_count,
            "total_bytes": base.total_bytes,
        },
        "model_tree": model_tree.as_dict(),
        "tokenizer_tree": tokenizer_tree.as_dict(),
    }
    body["authority_sha256"] = _sha256(canonical_json_bytes(body))
    return PhoBertReleaseManifest.from_dict(body)


def _expected_bundle_inventory(
    manifest: PhoBertReleaseManifest,
) -> tuple[tuple[str, str, int, str], ...]:
    inventory: list[tuple[str, str, int, str]] = [
        (PHOBERT_RELEASE_MODEL_ROOT, "directory", 0, ""),
        (PHOBERT_RELEASE_TOKENIZER_ROOT, "directory", 0, ""),
    ]
    for authority in (manifest.model_tree, manifest.tokenizer_tree):
        inventory.extend(
            (
                f"{authority.relative_root}/{relative}",
                "directory",
                0,
                "",
            )
            for relative in authority.directories
        )
        inventory.extend(
            (
                f"{authority.relative_root}/{record.relative_path}",
                "file",
                record.bytes,
                record.sha256,
            )
            for record in authority.files
        )
    return tuple(sorted(inventory))


def _load_manifest_locked(root: Path) -> tuple[PhoBertReleaseManifest, bytes]:
    value, payload = _load_canonical_json(
        root / PHOBERT_RELEASE_MANIFEST_NAME,
        "PhoBERT release manifest",
    )
    return PhoBertReleaseManifest.from_dict(value), payload


def _verify_locked_bundle(
    root: Path,
    lease: _WindowsClosedTreeLease,
    *,
    expected_manifest: PhoBertReleaseManifest | None = None,
) -> _VerifiedBundleState:
    lease.assert_intact()
    manifest, manifest_payload = _load_manifest_locked(root)
    _reject_portable_payload_path_leakage(
        manifest_payload,
        "PhoBERT release manifest",
        relative_path=PHOBERT_RELEASE_MANIFEST_NAME,
    )
    if expected_manifest is not None and manifest != expected_manifest:
        raise PhoBertReleaseError("published release manifest drifted")

    root_files = {
        relative: (byte_count, digest)
        for relative, kind, byte_count, digest in lease.inventory
        if kind == "file" and "/" not in relative
    }
    expected_root_files = {
        PHOBERT_RELEASE_MANIFEST_NAME,
        PHOBERT_RELEASE_RUN_EVIDENCE_NAME,
        PHOBERT_RELEASE_RESOLVED_CONFIG_NAME,
        PHOBERT_RELEASE_TRAINER_STATE_NAME,
    }
    if set(root_files) != expected_root_files:
        raise PhoBertReleaseError("release root files differ from the fixed layout")

    _, evidence_payload = _load_canonical_json(
        root / PHOBERT_RELEASE_RUN_EVIDENCE_NAME,
        "copied run evidence",
    )
    _reject_portable_payload_path_leakage(
        evidence_payload,
        "copied run evidence",
        relative_path=PHOBERT_RELEASE_RUN_EVIDENCE_NAME,
        path_exceptions=_CANONICAL_RUN_EVIDENCE_PATH_EXCEPTIONS,
    )
    try:
        evidence = RunEvidence.model_validate_json(evidence_payload)
    except ValidationError as exc:
        raise PhoBertReleaseError("copied run evidence schema is invalid") from exc
    model_artifact, trainer_artifact, resolved_config_artifact = (
        _validate_finalized_phobert_run(evidence)
    )
    _, resolved_config_payload = _load_json(
        root / PHOBERT_RELEASE_RESOLVED_CONFIG_NAME,
        "copied resolved config",
    )
    _reject_portable_payload_path_leakage(
        resolved_config_payload,
        "copied resolved config",
        relative_path=PHOBERT_RELEASE_RESOLVED_CONFIG_NAME,
        path_exceptions=_CANONICAL_RUN_EVIDENCE_PATH_EXCEPTIONS,
    )
    try:
        controlled_config = ResumeControlledConfig.model_validate_json(
            resolved_config_payload
        )
    except ValidationError as exc:
        raise PhoBertReleaseError("copied resolved-config schema is invalid") from exc
    trainer_value, trainer_payload = _load_json(
        root / PHOBERT_RELEASE_TRAINER_STATE_NAME,
        "copied trainer state",
    )
    _reject_portable_payload_path_leakage(
        trainer_payload,
        "copied trainer state",
        relative_path=PHOBERT_RELEASE_TRAINER_STATE_NAME,
    )
    if not isinstance(trainer_value, dict):
        raise PhoBertReleaseError("copied trainer state must contain an object")
    global_step = _require_nonnegative_int(
        trainer_value.get("global_step"), "trainer-state global_step"
    )

    run = manifest.run
    if (
        _sha256(evidence_payload) != run["evidence_sha256"]
        or evidence.run_id != run["run_id"]
        or evidence.selected_checkpoint is None
        or evidence.selected_checkpoint.optimizer_step != run["selected_optimizer_step"]
        or global_step != run["global_optimizer_step"]
        or _sha256(resolved_config_payload) != run["resolved_config_sha256"]
        or resolved_config_artifact.sha256 != _sha256(resolved_config_payload)
        or evidence.resolved_config_sha256 != _sha256(resolved_config_payload)
        or _sha256(trainer_payload) != run["trainer_state_sha256"]
        or trainer_artifact.sha256 != _sha256(trainer_payload)
    ):
        raise PhoBertReleaseError("copied run/trainer authority drifted")

    selected = manifest.selected_model
    if (
        model_artifact.sha256 != selected["artifact_sha256"]
        or model_artifact.logical_name != selected["artifact_logical_name"]
        or model_artifact.relative_path != selected["source_relative_path"]
        or evidence.selected_checkpoint.artifact_identity
        != selected["checkpoint_identity"]
    ):
        raise PhoBertReleaseError("copied selected-artifact authority drifted")

    model_root = root / PHOBERT_RELEASE_MODEL_ROOT
    tokenizer_root = root / PHOBERT_RELEASE_TOKENIZER_ROOT
    _reject_tree_path_leakage(
        model_root,
        manifest.model_tree,
        lease,
        "copied model metadata",
    )
    _reject_tree_path_leakage(
        tokenizer_root,
        manifest.tokenizer_tree,
        lease,
        "copied tokenizer metadata",
    )
    model_content = build_model_checksum(model_root)
    tokenizer_content = build_model_checksum(tokenizer_root)
    if (
        model_content != manifest.model_tree.content_sha256
        or tokenizer_content != manifest.tokenizer_tree.content_sha256
    ):
        raise PhoBertReleaseError("release model/tokenizer content hash drifted")
    if (
        evidence.selected_checkpoint is None
        or _phobert_model_state_identity(model_root)
        != evidence.selected_checkpoint.artifact_identity
    ):
        raise PhoBertReleaseError(
            "release model bytes differ from the checkpoint identity"
        )
    _validate_tokenizer_authority(manifest.tokenizer_tree)

    _, base_payload = _load_canonical_json(
        model_root / PHOBERT_BASE_MODEL_MANIFEST_NAME,
        "copied base-model provenance",
    )
    _reject_portable_payload_path_leakage(
        base_payload,
        "copied base-model provenance",
        relative_path=PHOBERT_BASE_MODEL_MANIFEST_NAME,
    )
    try:
        base = PhoBertBaseModelProvenance.model_validate_json(base_payload)
    except ValidationError as exc:
        raise PhoBertReleaseError("copied base-model provenance schema is invalid") from exc
    base_authority = manifest.base_model
    if (
        _sha256(base_payload) != base_authority["provenance_sha256"]
        or base.model_id != base_authority["model_id"]
        or base.model_revision != base_authority["model_revision"]
        or base.local_path_sha256 != base_authority["local_path_sha256"]
        or base.content_sha256 != base_authority["snapshot_sha256"]
        or base.file_count != base_authority["file_count"]
        or base.total_bytes != base_authority["total_bytes"]
        or manifest.preprocessor_sha256 != evidence.prompt_or_preprocessor_sha256
    ):
        raise PhoBertReleaseError("copied base/preprocessor authority drifted")

    expected_nested = _expected_bundle_inventory(manifest)
    actual_nested = tuple(
        item
        for item in lease.inventory
        if item[0] not in expected_root_files
    )
    if actual_nested != expected_nested:
        raise PhoBertReleaseError("release bundle inventory differs from manifest")
    if root_files[PHOBERT_RELEASE_MANIFEST_NAME] != (
        len(manifest_payload),
        _sha256(manifest_payload),
    ):
        raise PhoBertReleaseError("release manifest file authority drifted")
    if root_files[PHOBERT_RELEASE_RUN_EVIDENCE_NAME] != (
        len(evidence_payload),
        _sha256(evidence_payload),
    ) or root_files[PHOBERT_RELEASE_RESOLVED_CONFIG_NAME] != (
        len(resolved_config_payload),
        _sha256(resolved_config_payload),
    ) or root_files[PHOBERT_RELEASE_TRAINER_STATE_NAME] != (
        len(trainer_payload),
        _sha256(trainer_payload),
    ):
        raise PhoBertReleaseError("release root evidence inventory drifted")

    lease.assert_intact()
    bundle_sha256 = build_model_checksum(root)
    lease.assert_intact()
    return _VerifiedBundleState(
        root=root,
        manifest=manifest,
        manifest_sha256=_sha256(manifest_payload),
        bundle_root_sha256=bundle_sha256,
        evidence=evidence,
        controlled_config=controlled_config,
    )


def _receipt_for_bundle(bundle: _VerifiedBundleState) -> PhoBertReleaseReceipt:
    manifest = bundle.manifest
    body = {
        "schema_version": PHOBERT_RELEASE_RECEIPT_SCHEMA_VERSION,
        "role": "phobert",
        "bundle_relative_path": PHOBERT_RELEASE_BUNDLE_RELATIVE_PATH,
        "bundle_manifest_relative_path": (
            f"{PHOBERT_RELEASE_BUNDLE_RELATIVE_PATH}/{PHOBERT_RELEASE_MANIFEST_NAME}"
        ),
        "model_artifact_relative_path": (
            f"{PHOBERT_RELEASE_BUNDLE_RELATIVE_PATH}/{PHOBERT_RELEASE_MODEL_ROOT}"
        ),
        "tokenizer_relative_path": (
            f"{PHOBERT_RELEASE_BUNDLE_RELATIVE_PATH}/{PHOBERT_RELEASE_TOKENIZER_ROOT}"
        ),
        "upstream": dict(manifest.upstream),
        "bundle_manifest_sha256": bundle.manifest_sha256,
        "bundle_manifest_authority_sha256": manifest.authority_sha256,
        "bundle_root_sha256": bundle.bundle_root_sha256,
        "selected_run_id": manifest.run["run_id"],
        "selected_artifact_sha256": manifest.selected_model["artifact_sha256"],
        "tokenizer_sha256": manifest.tokenizer_tree.content_sha256,
        "run_evidence_sha256": manifest.run["evidence_sha256"],
        "resolved_config_sha256": manifest.run["resolved_config_sha256"],
        "selected_checkpoint_identity": manifest.selected_model[
            "checkpoint_identity"
        ],
        "base_provenance_sha256": manifest.base_model["provenance_sha256"],
        "base_snapshot_sha256": manifest.base_model["snapshot_sha256"],
        "preprocessor_sha256": manifest.preprocessor_sha256,
    }
    body["authority_sha256"] = _sha256(canonical_json_bytes(body))
    return PhoBertReleaseReceipt.from_dict(body)


def _load_receipt_locked(path: Path) -> tuple[PhoBertReleaseReceipt, bytes]:
    value, payload = _load_canonical_json(path, "PhoBERT release receipt")
    return PhoBertReleaseReceipt.from_dict(value), payload


def _verified_release(
    bundle: _VerifiedBundleState,
    receipt_path: Path,
    receipt: PhoBertReleaseReceipt,
    receipt_payload: bytes,
) -> VerifiedPhoBertReleaseBundle:
    expected = _receipt_for_bundle(bundle)
    if receipt != expected:
        raise PhoBertReleaseError("portable receipt differs from the verified bundle")
    return VerifiedPhoBertReleaseBundle(
        root=bundle.root,
        manifest=bundle.manifest,
        manifest_sha256=bundle.manifest_sha256,
        bundle_root_sha256=bundle.bundle_root_sha256,
        receipt_path=receipt_path,
        receipt=receipt,
        receipt_sha256=_sha256(receipt_payload),
    )


def _move_path_write_through(source: Path, destination: Path) -> None:
    if os.name != "nt":
        raise PhoBertReleaseError("release publication requires Windows")
    import ctypes
    from ctypes import wintypes

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.MoveFileExW.argtypes = [wintypes.LPCWSTR, wintypes.LPCWSTR, wintypes.DWORD]
    kernel32.MoveFileExW.restype = wintypes.BOOL
    if not kernel32.MoveFileExW(str(source), str(destination), 0x00000008):
        code = ctypes.get_last_error()
        raise PhoBertReleaseError(
            f"PhoBERT release publication failed atomically: winerror={code}"
        )


def build_phobert_release_bundle(
    *,
    repo_root: Path,
    transfer_root: Path,
    run_evidence_path: Path,
    selected_model_root: Path,
    tokenizer_root: Path,
    base_provenance_path: Path,
) -> VerifiedPhoBertReleaseBundle:
    """Publish the fixed external bundle, then its portable repo commit receipt."""

    repository = _lexical_absolute(repo_root, "repository root")
    transfer = _lexical_absolute(transfer_root, "verified transfer root")
    evidence_path = _lexical_absolute(run_evidence_path, "run evidence path")
    model_root = _lexical_absolute(selected_model_root, "selected model root")
    tokenizer = _lexical_absolute(tokenizer_root, "tokenizer root")
    base_path = _lexical_absolute(base_provenance_path, "base provenance path")
    output = _lexical_absolute(
        transfer / PurePosixPath(PHOBERT_RELEASE_BUNDLE_RELATIVE_PATH),
        "fixed release output root",
    )
    receipt_path = _lexical_absolute(
        repository / PurePosixPath(PHOBERT_RELEASE_RECEIPT_RELATIVE_PATH),
        "fixed release receipt path",
    )
    final_authority_path, origin_request_path = _upstream_paths(repository)
    run_root = evidence_path.parent
    expected_run_root = _lexical_absolute(
        transfer / PurePosixPath(_final_authority.PHOBERT_RETURNED_ROOT),
        "fixed PhoBERT v12 returned root",
    )

    _require_disjoint(repository, transfer, "repository and transfer roots")
    if evidence_path.name != PHOBERT_RELEASE_RUN_EVIDENCE_NAME:
        raise PhoBertReleaseError("selected evidence must be canonical run-evidence.json")
    if not _same_path(run_root, expected_run_root):
        raise PhoBertReleaseError(
            "PhoBERT source run must be the fixed v12 returned-root descendant"
        )
    _require_disjoint(output, run_root, "release output and run root")
    _require_disjoint(output, tokenizer, "release output and tokenizer root")
    _require_disjoint(model_root, tokenizer, "selected model and tokenizer roots")

    stage = output.parent / f".{output.name}.stage-{uuid.uuid4().hex}"
    receipt_stage = receipt_path.parent / f".{receipt_path.name}.stage-{uuid.uuid4().hex}"

    with ExitStack() as sources:
        repository_lease = sources.enter_context(
            _WindowsPathLease(
                repository,
                "verified repository root",
                expected_directory=True,
                deny_write=False,
            )
        )
        transfer_lease = sources.enter_context(
            _WindowsPathLease(
                transfer,
                "verified transfer root",
                expected_directory=True,
                deny_write=False,
            )
        )
        output_parent_lease = sources.enter_context(
            _WindowsPathLease(
                output.parent,
                "release output parent",
                expected_directory=True,
                deny_write=False,
            )
        )
        receipt_parent_lease = sources.enter_context(
            _WindowsPathLease(
                receipt_path.parent,
                "release receipt parent",
                expected_directory=True,
                deny_write=False,
            )
        )
        _require_path_absent_no_follow(output, "release output")
        _require_path_absent_no_follow(receipt_path, "release receipt")
        _require_path_absent_no_follow(stage, "release staging root")
        _require_path_absent_no_follow(receipt_stage, "receipt staging path")
        final_authority_lease = sources.enter_context(
            _WindowsPathLease(
                final_authority_path,
                "final Phase40 comparison authority",
                expected_directory=False,
                deny_write=True,
            )
        )
        origin_request_lease = sources.enter_context(
            _WindowsPathLease(
                origin_request_path,
                "PhoBERT v12 origin run request",
                expected_directory=False,
                deny_write=True,
            )
        )
        run_lease = sources.enter_context(
            _WindowsClosedTreeLease(run_root, "verified Phase40 PhoBERT run")
        )
        model_lease = sources.enter_context(
            _WindowsClosedTreeLease(model_root, "selected PhoBERT model")
        )
        tokenizer_lease = sources.enter_context(
            _WindowsClosedTreeLease(tokenizer, "exact PhoBERT tokenizer")
        )
        base_lease = sources.enter_context(
            _WindowsPathLease(
                base_path,
                "base provenance manifest",
                expected_directory=False,
                deny_write=True,
            )
        )

        if not _same_path(model_root, run_root / "adapter-or-model"):
            raise PhoBertReleaseError(
                "selected model root does not match run-evidence artifact path"
            )
        _, evidence_payload = _load_canonical_json(
            evidence_path,
            "canonical Phase40 run evidence",
        )
        try:
            parsed_evidence = RunEvidence.model_validate_json(evidence_payload)
        except ValidationError as exc:
            raise PhoBertReleaseError("Phase40 run evidence schema is invalid") from exc
        verified_evidence = verify_phase40_bundle(
            run_root,
            evidence_path=evidence_path,
        )
        if parsed_evidence != verified_evidence:
            raise PhoBertReleaseError("Phase40 run evidence semantic read-back drifted")
        model_artifact, trainer_artifact, resolved_config_artifact = (
            _validate_finalized_phobert_run(verified_evidence)
        )
        resolved_config_path = run_root / resolved_config_artifact.relative_path
        _, resolved_config_payload = _load_json(
            resolved_config_path,
            "finalized resolved config",
        )
        try:
            controlled_config = ResumeControlledConfig.model_validate_json(
                resolved_config_payload
            )
        except ValidationError as exc:
            raise PhoBertReleaseError(
                "finalized resolved-config schema is invalid"
            ) from exc
        if _sha256(resolved_config_payload) != resolved_config_artifact.sha256:
            raise PhoBertReleaseError("resolved-config artifact hash drifted")
        upstream = _load_verified_upstream_authorities(
            repository,
            verified_evidence,
            controlled_config,
        )

        trainer_path = run_root / trainer_artifact.relative_path
        trainer_value, trainer_payload = _load_json(
            trainer_path,
            "finalized trainer state",
        )
        if not isinstance(trainer_value, dict):
            raise PhoBertReleaseError("trainer state must contain an object")
        global_step = _require_nonnegative_int(
            trainer_value.get("global_step"),
            "trainer-state global_step",
        )
        if _sha256(trainer_payload) != trainer_artifact.sha256:
            raise PhoBertReleaseError("trainer-state artifact hash drifted")

        _, base_payload = _load_canonical_json(
            base_path,
            "canonical base-model provenance",
        )
        try:
            base = PhoBertBaseModelProvenance.model_validate_json(base_payload)
        except ValidationError as exc:
            raise PhoBertReleaseError("base-model provenance schema is invalid") from exc
        if base.schema_version != PHOBERT_BASE_PROVENANCE_SCHEMA:
            raise PhoBertReleaseError("base-model provenance schema drifted")
        embedded_base_path = model_root / PHOBERT_BASE_MODEL_MANIFEST_NAME
        try:
            embedded_payload = embedded_base_path.read_bytes()
        except OSError as exc:
            raise PhoBertReleaseError(
                "selected model lacks embedded base provenance"
            ) from exc
        if embedded_payload != base_payload:
            raise PhoBertReleaseError(
                "selected model base provenance differs from explicit authority"
            )
        if (
            base.model_id != verified_evidence.model_id
            or base.model_revision != verified_evidence.model_revision
        ):
            raise PhoBertReleaseError("base and run model identities differ")

        model_tree = _tree_authority_from_lease(
            model_lease,
            PHOBERT_RELEASE_MODEL_ROOT,
        )
        tokenizer_tree = _tree_authority_from_lease(
            tokenizer_lease,
            PHOBERT_RELEASE_TOKENIZER_ROOT,
        )
        _validate_tokenizer_authority(tokenizer_tree)
        if model_tree.content_sha256 != model_artifact.sha256:
            raise PhoBertReleaseError(
                "selected model bytes differ from finalized artifact authority"
            )
        if (
            verified_evidence.selected_checkpoint is None
            or _phobert_model_state_identity(model_root)
            != verified_evidence.selected_checkpoint.artifact_identity
        ):
            raise PhoBertReleaseError(
                "selected model bytes differ from the checkpoint identity"
            )
        if verified_evidence.selected_checkpoint is None or (
            verified_evidence.selected_checkpoint.optimizer_step > global_step
        ):
            raise PhoBertReleaseError("selected checkpoint exceeds trainer global step")

        _reject_portable_payload_path_leakage(
            evidence_payload,
            "run-evidence provenance",
            relative_path=PHOBERT_RELEASE_RUN_EVIDENCE_NAME,
            path_exceptions=_CANONICAL_RUN_EVIDENCE_PATH_EXCEPTIONS,
        )
        _reject_portable_payload_path_leakage(
            resolved_config_payload,
            "resolved-config provenance",
            relative_path=PHOBERT_RELEASE_RESOLVED_CONFIG_NAME,
        )
        _reject_portable_payload_path_leakage(
            trainer_payload,
            "trainer-state provenance",
            relative_path=PHOBERT_RELEASE_TRAINER_STATE_NAME,
        )
        _reject_portable_payload_path_leakage(
            base_payload,
            "base-model provenance",
            relative_path=PHOBERT_BASE_MODEL_MANIFEST_NAME,
        )
        _reject_tree_path_leakage(
            model_root,
            model_tree,
            model_lease,
            "selected model metadata",
        )
        _reject_tree_path_leakage(
            tokenizer,
            tokenizer_tree,
            tokenizer_lease,
            "tokenizer metadata",
        )

        manifest = _manifest_for_sources(
            upstream=upstream,
            evidence=verified_evidence,
            evidence_payload=evidence_payload,
            resolved_config_payload=resolved_config_payload,
            trainer_payload=trainer_payload,
            global_step=global_step,
            model_artifact=model_artifact,
            base=base,
            base_payload=base_payload,
            model_tree=model_tree,
            tokenizer_tree=tokenizer_tree,
        )
        manifest_payload = canonical_json_bytes(manifest.as_dict())

        output_parent_lease.assert_intact()
        try:
            stage.mkdir()
        except OSError as exc:
            raise PhoBertReleaseError("release staging root could not be created") from exc

        stage_identity: tuple[int, int, int] | None = None
        with _WindowsPathLease(
            stage,
            "release staging root",
            expected_directory=True,
            deny_write=False,
        ) as stage_root_lease:
            stage_identity = stage_root_lease.leaf_identity
            _copy_tree_from_authority(
                model_root,
                stage / PHOBERT_RELEASE_MODEL_ROOT,
                model_tree,
                model_lease,
            )
            _copy_tree_from_authority(
                tokenizer,
                stage / PHOBERT_RELEASE_TOKENIZER_ROOT,
                tokenizer_tree,
                tokenizer_lease,
            )
            _write_exact_file(
                stage / PHOBERT_RELEASE_RUN_EVIDENCE_NAME,
                evidence_payload,
            )
            _write_exact_file(
                stage / PHOBERT_RELEASE_RESOLVED_CONFIG_NAME,
                resolved_config_payload,
            )
            _write_exact_file(
                stage / PHOBERT_RELEASE_TRAINER_STATE_NAME,
                trainer_payload,
            )
            _write_exact_file(
                stage / PHOBERT_RELEASE_MANIFEST_NAME,
                manifest_payload,
            )
            for lease in (run_lease, model_lease, tokenizer_lease):
                lease.assert_intact()
            base_lease.assert_intact()
            final_authority_lease.assert_intact()
            origin_request_lease.assert_intact()
            stage_root_lease.assert_intact()
            with _WindowsClosedTreeLease(
                stage,
                "staged PhoBERT release bundle",
            ) as stage_tree_lease:
                staged_bundle = _verify_locked_bundle(
                    stage,
                    stage_tree_lease,
                    expected_manifest=manifest,
                )

        if stage_identity is None:
            raise PhoBertReleaseError("release staging identity was not retained")
        receipt = _receipt_for_bundle(staged_bundle)
        receipt_payload = canonical_json_bytes(receipt.as_dict())
        _write_exact_file(receipt_stage, receipt_payload)
        with _WindowsPathLease(
            receipt_stage,
            "staged PhoBERT release receipt",
            expected_directory=False,
            deny_write=True,
        ) as staged_receipt_lease:
            receipt_identity = staged_receipt_lease.leaf_identity
            observed_receipt, observed_receipt_payload = _load_receipt_locked(
                receipt_stage
            )
            if observed_receipt != receipt or observed_receipt_payload != receipt_payload:
                raise PhoBertReleaseError("staged release receipt drifted")
            staged_receipt_lease.assert_intact()

        with _WindowsPathLease(
            stage,
            "publishable release staging root",
            expected_directory=True,
            deny_write=False,
            allow_leaf_delete=True,
        ) as publish_lease:
            if publish_lease.leaf_identity != stage_identity:
                raise PhoBertReleaseError("release staging root was swapped before publish")
            _require_path_absent_no_follow(
                output,
                "release destination before publish",
            )
            output_parent_lease.assert_intact()
            transfer_lease.assert_intact()
            _move_path_write_through(stage, output)
            if not publish_lease.same_object_at(output):
                raise PhoBertReleaseError("published release root identity drifted")
            final_bundle_lease = sources.enter_context(
                _WindowsClosedTreeLease(
                    output,
                    "published PhoBERT release bundle",
                )
            )
            result = _verify_locked_bundle(
                output,
                final_bundle_lease,
                expected_manifest=manifest,
            )
            if not publish_lease.same_object_at(output):
                raise PhoBertReleaseError("published release root was retargeted")

        if result.bundle_root_sha256 != staged_bundle.bundle_root_sha256:
            raise PhoBertReleaseError("published bundle hash differs from staged bundle")
        with _WindowsPathLease(
            receipt_stage,
            "publishable PhoBERT release receipt",
            expected_directory=False,
            deny_write=True,
            allow_leaf_delete=True,
        ) as publish_receipt_lease:
            if publish_receipt_lease.leaf_identity != receipt_identity:
                raise PhoBertReleaseError("release receipt was swapped before publish")
            _require_path_absent_no_follow(
                receipt_path,
                "release receipt destination before publish",
            )
            repository_lease.assert_intact()
            receipt_parent_lease.assert_intact()
            _move_path_write_through(receipt_stage, receipt_path)
            if not publish_receipt_lease.same_object_at(receipt_path):
                raise PhoBertReleaseError("published release receipt identity drifted")
            final_receipt_lease = sources.enter_context(
                _WindowsPathLease(
                    receipt_path,
                    "published PhoBERT release receipt",
                    expected_directory=False,
                    deny_write=True,
                )
            )
            final_receipt, final_receipt_payload = _load_receipt_locked(receipt_path)
            final_receipt_lease.assert_intact()
            if not publish_receipt_lease.same_object_at(receipt_path):
                raise PhoBertReleaseError("published release receipt was retargeted")

        final_bundle_lease.assert_intact()
        final_receipt_lease.assert_intact()
        final_bundle = _verify_locked_bundle(
            output,
            final_bundle_lease,
            expected_manifest=manifest,
        )
        final_receipt, final_receipt_payload = _load_receipt_locked(receipt_path)
        verified = _verified_release(
            final_bundle,
            receipt_path,
            final_receipt,
            final_receipt_payload,
        )
        if final_bundle.bundle_root_sha256 != staged_bundle.bundle_root_sha256:
            raise PhoBertReleaseError("terminal bundle hash differs from staged bundle")
        final_bundle_lease.assert_intact()
        final_receipt_lease.assert_intact()

        output_parent_lease.assert_intact()
        receipt_parent_lease.assert_intact()
        repository_lease.assert_intact()
        transfer_lease.assert_intact()
        for lease in (run_lease, model_lease, tokenizer_lease):
            lease.assert_intact()
        base_lease.assert_intact()
        terminal_upstream = _load_verified_upstream_authorities(
            repository,
            verified_evidence,
            controlled_config,
        )
        if terminal_upstream != upstream:
            raise PhoBertReleaseError(
                "Phase40 final/recovery authority changed during publication"
            )
        final_authority_lease.assert_intact()
        origin_request_lease.assert_intact()
        return verified


def verify_phobert_release_bundle(
    *,
    repo_root: Path,
    transfer_root: Path,
) -> VerifiedPhoBertReleaseBundle:
    """Verify the fixed external bundle and portable repository receipt together."""

    repository = _lexical_absolute(repo_root, "repository root")
    transfer = _lexical_absolute(transfer_root, "verified transfer root")
    _require_disjoint(repository, transfer, "repository and transfer roots")
    root = _lexical_absolute(
        transfer / PurePosixPath(PHOBERT_RELEASE_BUNDLE_RELATIVE_PATH),
        "fixed release bundle root",
    )
    receipt_path = _lexical_absolute(
        repository / PurePosixPath(PHOBERT_RELEASE_RECEIPT_RELATIVE_PATH),
        "fixed release receipt path",
    )
    final_authority_path, origin_request_path = _upstream_paths(repository)
    with ExitStack() as stack:
        repository_lease = stack.enter_context(
            _WindowsPathLease(
                repository,
                "verified repository root",
                expected_directory=True,
                deny_write=False,
            )
        )
        transfer_lease = stack.enter_context(
            _WindowsPathLease(
                transfer,
                "verified transfer root",
                expected_directory=True,
                deny_write=False,
            )
        )
        receipt_lease = stack.enter_context(
            _WindowsPathLease(
                receipt_path,
                "portable PhoBERT release receipt",
                expected_directory=False,
                deny_write=True,
            )
        )
        final_authority_lease = stack.enter_context(
            _WindowsPathLease(
                final_authority_path,
                "final Phase40 comparison authority",
                expected_directory=False,
                deny_write=True,
            )
        )
        origin_request_lease = stack.enter_context(
            _WindowsPathLease(
                origin_request_path,
                "PhoBERT v12 origin run request",
                expected_directory=False,
                deny_write=True,
            )
        )
        try:
            bundle_lease = stack.enter_context(
                _WindowsClosedTreeLease(root, "PhoBERT release bundle")
            )
        except ReleaseAuthorityError as exc:
            raise PhoBertReleaseError(
                "fixed release bundle is missing or unsafe"
            ) from exc
        bundle = _verify_locked_bundle(root, bundle_lease)
        upstream = _load_verified_upstream_authorities(
            repository,
            bundle.evidence,
            bundle.controlled_config,
        )
        if upstream.as_dict() != bundle.manifest.upstream:
            raise PhoBertReleaseError("bundle is stale for canonical Phase40 upstream")
        receipt, receipt_payload = _load_receipt_locked(receipt_path)
        verified = _verified_release(
            bundle,
            receipt_path,
            receipt,
            receipt_payload,
        )
        repository_lease.assert_intact()
        transfer_lease.assert_intact()
        receipt_lease.assert_intact()
        final_authority_lease.assert_intact()
        origin_request_lease.assert_intact()
        bundle_lease.assert_intact()
        return verified


def load_phobert_release_manifest(
    *,
    transfer_root: Path,
) -> PhoBertReleaseManifest:
    """Load the fixed external manifest without claiming bundle validity."""

    transfer = _lexical_absolute(transfer_root, "verified transfer root")
    path = _lexical_absolute(
        transfer
        / PurePosixPath(PHOBERT_RELEASE_BUNDLE_RELATIVE_PATH)
        / PHOBERT_RELEASE_MANIFEST_NAME,
        "fixed release manifest path",
    )
    with ExitStack() as stack:
        transfer_lease = stack.enter_context(
            _WindowsPathLease(
                transfer,
                "verified transfer root",
                expected_directory=True,
                deny_write=False,
            )
        )
        lease = stack.enter_context(
            _WindowsPathLease(
                path,
                "fixed release manifest path",
                expected_directory=False,
                deny_write=True,
            )
        )
        value, _ = _load_canonical_json(path, "PhoBERT release manifest")
        manifest = PhoBertReleaseManifest.from_dict(value)
        transfer_lease.assert_intact()
        lease.assert_intact()
        return manifest


def load_phobert_release_receipt(
    *,
    repo_root: Path,
) -> PhoBertReleaseReceipt:
    """Load the portable byte authority after reverifying its fixed upstream.

    This deliberately does not claim that the off-repository bundle bytes are
    present or valid; :func:`verify_phobert_release_bundle` owns that stronger
    claim.
    """

    repository = _lexical_absolute(repo_root, "repository root")
    path = _lexical_absolute(
        repository / PurePosixPath(PHOBERT_RELEASE_RECEIPT_RELATIVE_PATH),
        "fixed release receipt path",
    )
    final_authority_path, origin_request_path = _upstream_paths(repository)
    with ExitStack() as stack:
        repository_lease = stack.enter_context(
            _WindowsPathLease(
                repository,
                "verified repository root",
                expected_directory=True,
                deny_write=False,
            )
        )
        lease = stack.enter_context(
            _WindowsPathLease(
                path,
                "fixed release receipt path",
                expected_directory=False,
                deny_write=True,
            )
        )
        final_authority_lease = stack.enter_context(
            _WindowsPathLease(
                final_authority_path,
                "final Phase40 comparison authority",
                expected_directory=False,
                deny_write=True,
            )
        )
        origin_request_lease = stack.enter_context(
            _WindowsPathLease(
                origin_request_path,
                "PhoBERT v12 origin run request",
                expected_directory=False,
                deny_write=True,
            )
        )
        receipt, _ = _load_receipt_locked(path)
        upstream = _load_verified_upstream_authorities(repository, None)
        if upstream.as_dict() != receipt.upstream:
            raise PhoBertReleaseError(
                "portable receipt is stale for the final PhoBERT v12 authority"
            )
        repository_lease.assert_intact()
        lease.assert_intact()
        final_authority_lease.assert_intact()
        origin_request_lease.assert_intact()
        return receipt


__all__ = [
    "PHOBERT_RELEASE_BUNDLE_RELATIVE_PATH",
    "PHOBERT_RELEASE_MANIFEST_NAME",
    "PHOBERT_RELEASE_MODEL_ROOT",
    "PHOBERT_RELEASE_ORIGIN_REQUEST_RELATIVE_PATH",
    "PHOBERT_RELEASE_RECEIPT_RELATIVE_PATH",
    "PHOBERT_RELEASE_RECEIPT_SCHEMA_VERSION",
    "PHOBERT_RELEASE_RESOLVED_CONFIG_NAME",
    "PHOBERT_RELEASE_RUN_EVIDENCE_NAME",
    "PHOBERT_RELEASE_SCHEMA_VERSION",
    "PHOBERT_RELEASE_TOKENIZER_ROOT",
    "PHOBERT_RELEASE_TRAINER_STATE_NAME",
    "PhoBertReleaseError",
    "PhoBertReleaseManifest",
    "PhoBertReleaseReceipt",
    "ReleaseFileRecord",
    "ReleaseTreeAuthority",
    "VerifiedPhoBertReleaseBundle",
    "build_phobert_release_bundle",
    "load_phobert_release_manifest",
    "load_phobert_release_receipt",
    "verify_phobert_release_bundle",
]
