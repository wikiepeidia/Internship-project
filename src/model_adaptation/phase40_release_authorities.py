"""Canonical release authorities for the frozen Phase 40 Python runtime.

The capture surface is deliberately explicit.  Callers provide a Python binary,
the exact dependency closure, and every file declared by each distribution.  No
function in this module discovers or inventories the ambient Python environment.
"""

from __future__ import annotations

from contextlib import ExitStack
from dataclasses import dataclass
import hashlib
import json
import math
import os
from pathlib import Path, PurePosixPath
import re
import stat
from typing import Mapping, Sequence


RUNTIME_AUTHORITY_SCHEMA_VERSION = "phase40-runtime-dependency-authority-v1"
SEGMENTER_AUTHORITY_SCHEMA_VERSION = "phase40-segmenter-authority-v1"
PYTHON_AUTHORITY_SCHEMA_VERSION = "phase40-python-runtime-authority-v1"
DISTRIBUTION_AUTHORITY_SCHEMA_VERSION = "phase40-distribution-authority-v1"
RUNTIME_AUTHORITY_FILENAME = "runtime-dependency-authority.json"
SEGMENTER_DISTRIBUTION = "underthesea"

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_DISTRIBUTION_NORMALIZER = re.compile(r"[-_.]+")
_VERSION_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9.!+_-]*$")
_IDENTITY_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._+-]*$")


class ReleaseAuthorityError(ValueError):
    """A release authority or one of its explicitly bound files is unsafe."""


def _reject_duplicate_keys(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ReleaseAuthorityError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _require_portable(value: object, *, location: str = "$") -> None:
    if value is None or isinstance(value, (bool, int, str)):
        if isinstance(value, str) and "\x00" in value:
            raise ReleaseAuthorityError(f"NUL is forbidden at {location}")
        return
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ReleaseAuthorityError(f"non-finite JSON value at {location}")
        return
    if isinstance(value, Mapping):
        for key, item in value.items():
            if not isinstance(key, str) or not key:
                raise ReleaseAuthorityError(
                    f"authority keys must be non-empty strings at {location}"
                )
            _require_portable(item, location=f"{location}.{key}")
        return
    if isinstance(value, (list, tuple)):
        for index, item in enumerate(value):
            _require_portable(item, location=f"{location}[{index}]")
        return
    raise ReleaseAuthorityError(
        f"unsupported authority value at {location}: {type(value).__name__}"
    )


def canonical_json_bytes(value: object) -> bytes:
    """Return the only accepted JSON representation for release authorities."""

    _require_portable(value)
    try:
        text = json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
    except (TypeError, ValueError) as exc:
        raise ReleaseAuthorityError("authority is not canonical JSON data") from exc
    return text.encode("utf-8", errors="strict") + b"\n"


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _require_sha256(value: object, description: str) -> str:
    if not isinstance(value, str) or not _SHA256_RE.fullmatch(value):
        raise ReleaseAuthorityError(f"{description} must be a lowercase SHA-256")
    return value


def _require_exact_keys(
    value: object,
    expected: frozenset[str],
    description: str,
) -> dict[str, object]:
    if not isinstance(value, dict) or set(value) != expected:
        raise ReleaseAuthorityError(f"{description} fields differ from schema")
    return value


def _require_text(value: object, description: str, *, allow_empty: bool = False) -> str:
    if not isinstance(value, str) or "\x00" in value:
        raise ReleaseAuthorityError(f"{description} must be text")
    if not allow_empty and not value:
        raise ReleaseAuthorityError(f"{description} must be non-empty")
    if value != value.strip() or any(ord(character) < 32 for character in value):
        raise ReleaseAuthorityError(f"{description} is not canonical text")
    return value


def normalize_distribution_name(value: str) -> str:
    """Apply the canonical Python distribution-name normalization."""

    name = _require_text(value, "distribution name")
    normalized = _DISTRIBUTION_NORMALIZER.sub("-", name).lower()
    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", normalized):
        raise ReleaseAuthorityError("distribution name is invalid")
    return normalized


def _require_version(value: object, description: str) -> str:
    version = _require_text(value, description)
    if not _VERSION_RE.fullmatch(version):
        raise ReleaseAuthorityError(f"{description} is invalid")
    return version


def _require_relative_path(value: object, description: str) -> str:
    path = _require_text(value, description)
    if "\\" in path or ":" in path or path.startswith("/"):
        raise ReleaseAuthorityError(f"{description} is not canonical relative POSIX")
    components = path.split("/")
    if any(not component or component in {".", ".."} for component in components):
        raise ReleaseAuthorityError(f"{description} is not canonical relative POSIX")
    if PurePosixPath(path).as_posix() != path:
        raise ReleaseAuthorityError(f"{description} is not canonical relative POSIX")
    return path


def _require_nonnegative_int(value: object, description: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise ReleaseAuthorityError(f"{description} must be a non-negative integer")
    return value


@dataclass(frozen=True, slots=True)
class PythonCaptureInput:
    """Explicit identity plus a dedicated, closed Python runtime tree."""

    implementation: str
    version: str
    cache_tag: str
    abi_flags: str
    platform: str
    executable_root: Path
    executable: Path


@dataclass(frozen=True, slots=True)
class DistributionCaptureInput:
    """One dedicated closed tree and its independently declared membership."""

    name: str
    version: str
    install_root: Path
    import_origin: Path
    declared_files: Sequence[Path]


@dataclass(frozen=True, slots=True)
class FileAuthority:
    relative_path: str
    bytes: int
    sha256: str

    def __post_init__(self) -> None:
        _require_relative_path(self.relative_path, "file relative_path")
        _require_nonnegative_int(self.bytes, "file bytes")
        _require_sha256(self.sha256, "file sha256")

    def as_dict(self) -> dict[str, object]:
        return {
            "relative_path": self.relative_path,
            "bytes": self.bytes,
            "sha256": self.sha256,
        }

    @classmethod
    def from_dict(cls, value: object) -> FileAuthority:
        body = _require_exact_keys(
            value,
            frozenset({"relative_path", "bytes", "sha256"}),
            "file authority",
        )
        return cls(
            relative_path=body["relative_path"],  # type: ignore[arg-type]
            bytes=body["bytes"],  # type: ignore[arg-type]
            sha256=body["sha256"],  # type: ignore[arg-type]
        )


@dataclass(frozen=True, slots=True)
class PythonRuntimeAuthority:
    implementation: str
    version: str
    cache_tag: str
    abi_flags: str
    platform: str
    executable: FileAuthority
    files: tuple[FileAuthority, ...]
    tree_sha256: str
    identity_sha256: str
    schema_version: str = PYTHON_AUTHORITY_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.schema_version != PYTHON_AUTHORITY_SCHEMA_VERSION:
            raise ReleaseAuthorityError("unsupported Python authority schema")
        implementation = _require_text(self.implementation, "Python implementation")
        if not _IDENTITY_RE.fullmatch(implementation):
            raise ReleaseAuthorityError("Python implementation is invalid")
        _require_version(self.version, "Python version")
        cache_tag = _require_text(self.cache_tag, "Python cache_tag")
        if not _IDENTITY_RE.fullmatch(cache_tag):
            raise ReleaseAuthorityError("Python cache_tag is invalid")
        _require_text(self.abi_flags, "Python abi_flags", allow_empty=True)
        _require_text(self.platform, "Python platform")
        if not isinstance(self.executable, FileAuthority) or self.executable.bytes == 0:
            raise ReleaseAuthorityError("Python executable must be a non-empty regular file")
        if any(not isinstance(item, FileAuthority) for item in self.files):
            raise ReleaseAuthorityError("Python runtime file inventory is malformed")
        paths = tuple(item.relative_path for item in self.files)
        if (
            not paths
            or paths != tuple(sorted(paths))
            or len(paths) != len(set(paths))
        ):
            raise ReleaseAuthorityError(
                "Python runtime file inventory is duplicate or noncanonical"
            )
        matching_executables = tuple(
            item for item in self.files if item.relative_path == self.executable.relative_path
        )
        if matching_executables != (self.executable,):
            raise ReleaseAuthorityError("Python executable is not bound into its runtime tree")
        if self.tree_sha256 != _python_tree_sha256(self.files):
            raise ReleaseAuthorityError("Python runtime tree hash mismatch")
        expected = _sha256(canonical_json_bytes(self._body_without_hash()))
        if self.identity_sha256 != expected:
            raise ReleaseAuthorityError("Python runtime identity self-hash mismatch")

    def _body_without_hash(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "implementation": self.implementation,
            "version": self.version,
            "cache_tag": self.cache_tag,
            "abi_flags": self.abi_flags,
            "platform": self.platform,
            "executable": self.executable.as_dict(),
            "files": [item.as_dict() for item in self.files],
            "tree_sha256": self.tree_sha256,
        }

    def as_dict(self) -> dict[str, object]:
        body = self._body_without_hash()
        body["identity_sha256"] = self.identity_sha256
        return body

    @classmethod
    def from_dict(cls, value: object) -> PythonRuntimeAuthority:
        body = _require_exact_keys(
            value,
            frozenset(
                {
                    "schema_version",
                    "implementation",
                    "version",
                    "cache_tag",
                    "abi_flags",
                    "platform",
                    "executable",
                    "files",
                    "tree_sha256",
                    "identity_sha256",
                }
            ),
            "Python runtime authority",
        )
        raw_files = body["files"]
        if not isinstance(raw_files, list):
            raise ReleaseAuthorityError("Python runtime files must be a list")
        return cls(
            implementation=body["implementation"],  # type: ignore[arg-type]
            version=body["version"],  # type: ignore[arg-type]
            cache_tag=body["cache_tag"],  # type: ignore[arg-type]
            abi_flags=body["abi_flags"],  # type: ignore[arg-type]
            platform=body["platform"],  # type: ignore[arg-type]
            executable=FileAuthority.from_dict(body["executable"]),
            files=tuple(FileAuthority.from_dict(item) for item in raw_files),
            tree_sha256=body["tree_sha256"],  # type: ignore[arg-type]
            identity_sha256=body["identity_sha256"],  # type: ignore[arg-type]
            schema_version=body["schema_version"],  # type: ignore[arg-type]
        )


@dataclass(frozen=True, slots=True)
class DistributionAuthority:
    name: str
    version: str
    import_origin: str
    files: tuple[FileAuthority, ...]
    tree_sha256: str
    authority_sha256: str
    schema_version: str = DISTRIBUTION_AUTHORITY_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.schema_version != DISTRIBUTION_AUTHORITY_SCHEMA_VERSION:
            raise ReleaseAuthorityError("unsupported distribution authority schema")
        if normalize_distribution_name(self.name) != self.name:
            raise ReleaseAuthorityError("distribution name is not normalized")
        _require_version(self.version, f"{self.name} version")
        origin = _require_relative_path(self.import_origin, f"{self.name} import origin")
        if not self.files:
            raise ReleaseAuthorityError(f"{self.name} file inventory is empty")
        if any(not isinstance(item, FileAuthority) for item in self.files):
            raise ReleaseAuthorityError(f"{self.name} file inventory is malformed")
        paths = tuple(item.relative_path for item in self.files)
        if paths != tuple(sorted(paths)) or len(paths) != len(set(paths)):
            raise ReleaseAuthorityError(
                f"{self.name} file inventory is duplicate or noncanonical"
            )
        if origin not in set(paths):
            raise ReleaseAuthorityError(f"{self.name} import origin is not declared")
        expected_tree = _distribution_tree_sha256(self.files)
        if self.tree_sha256 != expected_tree:
            raise ReleaseAuthorityError(f"{self.name} distribution tree hash mismatch")
        expected_authority = _sha256(canonical_json_bytes(self._body_without_hash()))
        if self.authority_sha256 != expected_authority:
            raise ReleaseAuthorityError(f"{self.name} authority self-hash mismatch")

    def _body_without_hash(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "name": self.name,
            "version": self.version,
            "import_origin": self.import_origin,
            "files": [item.as_dict() for item in self.files],
            "tree_sha256": self.tree_sha256,
        }

    def as_dict(self) -> dict[str, object]:
        body = self._body_without_hash()
        body["authority_sha256"] = self.authority_sha256
        return body

    @classmethod
    def from_dict(cls, value: object) -> DistributionAuthority:
        body = _require_exact_keys(
            value,
            frozenset(
                {
                    "schema_version",
                    "name",
                    "version",
                    "import_origin",
                    "files",
                    "tree_sha256",
                    "authority_sha256",
                }
            ),
            "distribution authority",
        )
        raw_files = body["files"]
        if not isinstance(raw_files, list):
            raise ReleaseAuthorityError("distribution files must be a list")
        return cls(
            name=body["name"],  # type: ignore[arg-type]
            version=body["version"],  # type: ignore[arg-type]
            import_origin=body["import_origin"],  # type: ignore[arg-type]
            files=tuple(FileAuthority.from_dict(item) for item in raw_files),
            tree_sha256=body["tree_sha256"],  # type: ignore[arg-type]
            authority_sha256=body["authority_sha256"],  # type: ignore[arg-type]
            schema_version=body["schema_version"],  # type: ignore[arg-type]
        )


@dataclass(frozen=True, slots=True)
class SegmenterAuthority:
    distribution_name: str
    distribution_version: str
    import_origin: str
    distribution_tree_sha256: str
    distribution_authority_sha256: str
    authority_sha256: str
    schema_version: str = SEGMENTER_AUTHORITY_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.schema_version != SEGMENTER_AUTHORITY_SCHEMA_VERSION:
            raise ReleaseAuthorityError("unsupported segmenter authority schema")
        if self.distribution_name != SEGMENTER_DISTRIBUTION:
            raise ReleaseAuthorityError("segmenter must bind underthesea exactly")
        _require_version(self.distribution_version, "segmenter distribution version")
        _require_relative_path(self.import_origin, "segmenter import origin")
        _require_sha256(self.distribution_tree_sha256, "segmenter tree sha256")
        _require_sha256(
            self.distribution_authority_sha256,
            "segmenter distribution authority sha256",
        )
        expected = _sha256(canonical_json_bytes(self._body_without_hash()))
        if self.authority_sha256 != expected:
            raise ReleaseAuthorityError("segmenter authority self-hash mismatch")

    @property
    def segmenter_sha256(self) -> str:
        """Stable binding consumed by the Phase 41 PhoBERT protocol."""

        return self.authority_sha256

    def _body_without_hash(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "distribution_name": self.distribution_name,
            "distribution_version": self.distribution_version,
            "import_origin": self.import_origin,
            "distribution_tree_sha256": self.distribution_tree_sha256,
            "distribution_authority_sha256": self.distribution_authority_sha256,
        }

    def as_dict(self) -> dict[str, object]:
        body = self._body_without_hash()
        body["authority_sha256"] = self.authority_sha256
        return body

    @classmethod
    def from_dict(cls, value: object) -> SegmenterAuthority:
        body = _require_exact_keys(
            value,
            frozenset(
                {
                    "schema_version",
                    "distribution_name",
                    "distribution_version",
                    "import_origin",
                    "distribution_tree_sha256",
                    "distribution_authority_sha256",
                    "authority_sha256",
                }
            ),
            "segmenter authority",
        )
        return cls(
            distribution_name=body["distribution_name"],  # type: ignore[arg-type]
            distribution_version=body["distribution_version"],  # type: ignore[arg-type]
            import_origin=body["import_origin"],  # type: ignore[arg-type]
            distribution_tree_sha256=body["distribution_tree_sha256"],  # type: ignore[arg-type]
            distribution_authority_sha256=body[
                "distribution_authority_sha256"
            ],  # type: ignore[arg-type]
            authority_sha256=body["authority_sha256"],  # type: ignore[arg-type]
            schema_version=body["schema_version"],  # type: ignore[arg-type]
        )


@dataclass(frozen=True, slots=True)
class RuntimeDependencyAuthority:
    python: PythonRuntimeAuthority
    distributions: tuple[DistributionAuthority, ...]
    segmenter: SegmenterAuthority
    authority_sha256: str
    schema_version: str = RUNTIME_AUTHORITY_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.schema_version != RUNTIME_AUTHORITY_SCHEMA_VERSION:
            raise ReleaseAuthorityError("unsupported runtime authority schema")
        if not isinstance(self.python, PythonRuntimeAuthority):
            raise ReleaseAuthorityError("runtime Python authority is malformed")
        if any(
            not isinstance(item, DistributionAuthority)
            for item in self.distributions
        ):
            raise ReleaseAuthorityError("runtime distribution closure is malformed")
        names = tuple(item.name for item in self.distributions)
        if (
            not names
            or names != tuple(sorted(names))
            or len(names) != len(set(names))
        ):
            raise ReleaseAuthorityError(
                "runtime distribution closure is duplicate or noncanonical"
            )
        segmenter_distribution = next(
            (item for item in self.distributions if item.name == SEGMENTER_DISTRIBUTION),
            None,
        )
        if segmenter_distribution is None or self.segmenter != _segmenter_from_distribution(
            segmenter_distribution
        ):
            raise ReleaseAuthorityError(
                "segmenter authority does not match the underthesea distribution"
            )
        expected = _sha256(canonical_json_bytes(self._body_without_hash()))
        if self.authority_sha256 != expected:
            raise ReleaseAuthorityError("runtime authority self-hash mismatch")

    @property
    def segmenter_sha256(self) -> str:
        return self.segmenter.segmenter_sha256

    def _body_without_hash(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "python": self.python.as_dict(),
            "distributions": [item.as_dict() for item in self.distributions],
            "segmenter": self.segmenter.as_dict(),
        }

    def as_dict(self) -> dict[str, object]:
        body = self._body_without_hash()
        body["authority_sha256"] = self.authority_sha256
        return body

    @classmethod
    def from_dict(cls, value: object) -> RuntimeDependencyAuthority:
        body = _require_exact_keys(
            value,
            frozenset(
                {
                    "schema_version",
                    "python",
                    "distributions",
                    "segmenter",
                    "authority_sha256",
                }
            ),
            "runtime dependency authority",
        )
        raw_distributions = body["distributions"]
        if not isinstance(raw_distributions, list):
            raise ReleaseAuthorityError("runtime distributions must be a list")
        return cls(
            python=PythonRuntimeAuthority.from_dict(body["python"]),
            distributions=tuple(
                DistributionAuthority.from_dict(item) for item in raw_distributions
            ),
            segmenter=SegmenterAuthority.from_dict(body["segmenter"]),
            authority_sha256=body["authority_sha256"],  # type: ignore[arg-type]
            schema_version=body["schema_version"],  # type: ignore[arg-type]
        )


@dataclass(frozen=True, slots=True)
class _CapturedFile:
    authority: FileAuthority
    absolute_path_key: str
    physical_identity: tuple[int, int] | None


def _distribution_tree_sha256(files: Sequence[FileAuthority]) -> str:
    payload = canonical_json_bytes([item.as_dict() for item in files])
    return _sha256(b"phase40-distribution-tree-v1\0" + payload)


def _python_tree_sha256(files: Sequence[FileAuthority]) -> str:
    payload = canonical_json_bytes([item.as_dict() for item in files])
    return _sha256(b"phase40-python-runtime-tree-v1\0" + payload)


def _path_is_redirecting(path: Path) -> bool:
    try:
        if path.is_symlink():
            return True
        is_junction = getattr(path, "is_junction", None)
        if callable(is_junction) and is_junction():
            return True
        attributes = int(getattr(os.lstat(path), "st_file_attributes", 0))
    except OSError as exc:
        raise ReleaseAuthorityError(f"cannot inspect path safely: {path}") from exc
    return bool(attributes & 0x00000400)


def _lexical_absolute(path: Path) -> Path:
    return Path(os.path.abspath(os.path.normpath(os.fspath(path))))


def _path_key(path: Path) -> str:
    return os.path.normcase(os.fspath(_lexical_absolute(path)))


class _WindowsClosedTreeLease:
    """Retain non-delete-shared identities for one content-bound tree.

    The first inventory hashes every file before returning.  Entry handles are
    then retained and a second inventory must match, closing the otherwise
    mutable interval between directory enumeration and the first file handle.
    """

    __slots__ = (
        "root",
        "description",
        "inventory",
        "_closed",
        "_handles",
        "_info_type",
        "_kernel32",
    )

    def __init__(self, root: Path, description: str) -> None:
        if os.name != "nt":
            raise ReleaseAuthorityError(
                "closed release capture requires Windows handle enforcement"
            )
        self.root = Path(root)
        self.description = description
        self.inventory: tuple[tuple[str, str, int, str], ...] = ()
        self._closed = False
        self._handles: list[tuple[object, bool, tuple[int, int, int]]] = []
        self._kernel32 = None
        self._info_type = None
        try:
            self._configure_api()
            for ancestor in reversed((self.root, *self.root.parents)):
                self._hold_path(
                    ancestor,
                    expected_directory=True,
                    deny_write=False,
                )
            self.inventory = _closed_tree_inventory(self.root, self.description)
            for relative, kind, _, _ in self.inventory:
                self._hold_path(
                    self.root / relative,
                    expected_directory=kind == "directory",
                    deny_write=True,
                )
            self.assert_intact()
        except BaseException:
            self.close()
            raise

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
            raise ReleaseAuthorityError(
                f"{self.description} Windows handle API is unavailable"
            )
        information = self._info_type()
        if not self._kernel32.GetFileInformationByHandle(
            handle,
            ctypes.byref(information),
        ):
            code = ctypes.get_last_error()
            raise ReleaseAuthorityError(
                f"{self.description} held path cannot be inspected: winerror={code}"
            )
        attributes = int(information.dwFileAttributes)
        is_directory = bool(attributes & 0x00000010)
        if attributes & 0x00000400 or is_directory is not expected_directory:
            raise ReleaseAuthorityError(
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
    ) -> None:
        import ctypes

        if self._kernel32 is None:
            raise ReleaseAuthorityError(
                f"{self.description} Windows handle API is unavailable"
            )
        invalid = ctypes.c_void_p(-1).value
        handle = self._kernel32.CreateFileW(
            str(target),
            0x80000000,
            0x00000001 if deny_write else 0x00000003,
            None,
            3,
            0x00200000 | 0x02000000,
            None,
        )
        if handle == invalid:
            code = ctypes.get_last_error()
            raise ReleaseAuthorityError(
                f"{self.description} cannot lock ancestry/tree: winerror={code}"
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

    def assert_intact(self) -> None:
        expected_count = len((self.root, *self.root.parents)) + len(self.inventory)
        if self._closed or len(self._handles) != expected_count:
            raise ReleaseAuthorityError(
                f"{self.description} capture-time handle lease is closed"
            )
        for handle, expected_directory, expected_identity in self._handles:
            if (
                self._inspect_handle(
                    handle,
                    expected_directory=expected_directory,
                )
                != expected_identity
            ):
                raise ReleaseAuthorityError(
                    f"{self.description} held path identity drifted"
                )
        if _closed_tree_inventory(self.root, self.description) != self.inventory:
            raise ReleaseAuthorityError(
                f"{self.description} changed during its capture-time lease"
            )

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        if self._kernel32 is not None:
            while self._handles:
                handle, _, _ = self._handles.pop()
                self._kernel32.CloseHandle(handle)

    def __enter__(self) -> _WindowsClosedTreeLease:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def __del__(self) -> None:  # pragma: no cover - process-exit safety net
        try:
            self.close()
        except Exception:
            pass


def _validate_trusted_root(root: Path, description: str) -> Path:
    lexical = _lexical_absolute(Path(root))
    if (
        not Path(root).is_absolute()
        or lexical.parent == lexical
        or not lexical.is_dir()
    ):
        raise ReleaseAuthorityError(
            f"{description} must be an existing bounded absolute directory"
        )
    for ancestor in reversed((lexical, *lexical.parents)):
        if _path_is_redirecting(ancestor):
            raise ReleaseAuthorityError(f"{description} ancestry is symlink/reparse")
    return lexical


def _candidate_within_root(
    root: Path,
    candidate: Path,
    description: str,
) -> tuple[Path, str]:
    supplied = Path(candidate)
    if "\x00" in os.fspath(supplied) or ".." in supplied.parts:
        raise ReleaseAuthorityError(f"{description} is noncanonical or out-of-root")
    absolute = _lexical_absolute(supplied if supplied.is_absolute() else root / supplied)
    try:
        common = os.path.commonpath((os.fspath(root), os.fspath(absolute)))
    except ValueError as exc:
        raise ReleaseAuthorityError(f"{description} is out-of-root") from exc
    if os.path.normcase(common) != os.path.normcase(os.fspath(root)) or absolute == root:
        raise ReleaseAuthorityError(f"{description} is out-of-root")
    relative = os.path.relpath(absolute, root).replace(os.sep, "/")
    canonical_relative = _require_relative_path(relative, description)
    current = root
    for component in PurePosixPath(canonical_relative).parts:
        current = current / component
        if not current.exists() and not current.is_symlink():
            raise ReleaseAuthorityError(f"{description} is missing")
        if _path_is_redirecting(current):
            raise ReleaseAuthorityError(f"{description} is symlink/reparse")
    return absolute, canonical_relative


def _capture_regular_file(
    root: Path,
    candidate: Path,
    description: str,
) -> _CapturedFile:
    absolute, relative = _candidate_within_root(root, candidate, description)
    try:
        before = os.lstat(absolute)
        if not stat.S_ISREG(before.st_mode):
            raise ReleaseAuthorityError(f"{description} is not a regular file")
        digest = hashlib.sha256()
        byte_count = 0
        with absolute.open("rb") as handle:
            opened = os.fstat(handle.fileno())
            if not stat.S_ISREG(opened.st_mode):
                raise ReleaseAuthorityError(f"{description} opened as a special file")
            while chunk := handle.read(1024 * 1024):
                digest.update(chunk)
                byte_count += len(chunk)
        after = os.lstat(absolute)
    except OSError as exc:
        raise ReleaseAuthorityError(f"{description} could not be read safely") from exc
    stable_fields = ("st_dev", "st_ino", "st_size", "st_mtime_ns")
    if any(
        getattr(before, field, None) != getattr(opened, field, None)
        or getattr(opened, field, None) != getattr(after, field, None)
        for field in stable_fields
    ) or before.st_ctime_ns != after.st_ctime_ns or byte_count != before.st_size:
        raise ReleaseAuthorityError(f"{description} changed while being captured")
    inode = (int(before.st_dev), int(before.st_ino))
    return _CapturedFile(
        authority=FileAuthority(relative, byte_count, digest.hexdigest()),
        absolute_path_key=_path_key(absolute),
        physical_identity=inode if inode[1] else None,
    )


def _closed_tree_inventory(
    root: Path,
    description: str,
) -> tuple[tuple[str, str, int, str], ...]:
    try:
        entries = tuple(root.rglob("*"))
    except OSError as exc:
        raise ReleaseAuthorityError(f"{description} could not be enumerated") from exc
    inventory: list[tuple[str, str, int, str]] = []
    for entry in entries:
        relative = entry.relative_to(root).as_posix()
        if _path_is_redirecting(entry):
            raise ReleaseAuthorityError(f"{description} contains symlink/reparse")
        try:
            observed = os.lstat(entry)
        except OSError as exc:
            raise ReleaseAuthorityError(f"{description} entry vanished") from exc
        if stat.S_ISDIR(observed.st_mode):
            inventory.append((relative, "directory", 0, ""))
        elif stat.S_ISREG(observed.st_mode):
            captured = _capture_regular_file(
                root,
                Path(relative),
                f"{description} inventory file",
            ).authority
            inventory.append((relative, "file", captured.bytes, captured.sha256))
        else:
            raise ReleaseAuthorityError(f"{description} contains a special entry")
    return tuple(sorted(inventory))


def _capture_closed_tree(
    root: Path,
    description: str,
    *,
    lease: _WindowsClosedTreeLease | None = None,
) -> tuple[_CapturedFile, ...]:
    """Capture every regular entry and reject links or special/vanishing entries."""

    owns_lease = lease is None
    active_lease = lease or _WindowsClosedTreeLease(root, description)
    if active_lease.root != root or active_lease.description != description:
        if owns_lease:
            active_lease.close()
        raise ReleaseAuthorityError(f"{description} capture lease is misbound")
    try:
        try:
            captured = tuple(
                _capture_regular_file(
                    root,
                    Path(relative),
                    f"{description} regular file",
                )
                for relative, kind, _, _ in active_lease.inventory
                if kind == "file"
            )
        except OSError as exc:
            raise ReleaseAuthorityError(
                f"{description} changed while its files were captured"
            ) from exc
        active_lease.assert_intact()
    finally:
        if owns_lease:
            active_lease.close()
    if not captured:
        raise ReleaseAuthorityError(f"{description} has no regular files")
    expected_files = {
        relative: (byte_count, digest)
        for relative, kind, byte_count, digest in active_lease.inventory
        if kind == "file"
    }
    if any(
        expected_files.get(item.authority.relative_path)
        != (item.authority.bytes, item.authority.sha256)
        for item in captured
    ):
        raise ReleaseAuthorityError(
            f"{description} changed during its capture-time lease"
        )
    return captured


def _build_python_authority(
    capture: PythonCaptureInput,
    *,
    lease: _WindowsClosedTreeLease | None = None,
) -> tuple[PythonRuntimeAuthority, tuple[_CapturedFile, ...]]:
    root = _validate_trusted_root(capture.executable_root, "Python executable root")
    runtime_files = _capture_closed_tree(
        root,
        "Python runtime tree",
        lease=lease,
    )
    executable_absolute, executable_relative = _candidate_within_root(
        root,
        capture.executable,
        "Python executable",
    )
    executable = next(
        (
            item
            for item in runtime_files
            if item.authority.relative_path == executable_relative
            and item.absolute_path_key == _path_key(executable_absolute)
        ),
        None,
    )
    if executable is None or executable.authority.bytes == 0:
        raise ReleaseAuthorityError(
            "Python executable is absent from the closed runtime tree"
        )
    files = tuple(item.authority for item in runtime_files)
    tree_sha256 = _python_tree_sha256(files)
    body = {
        "schema_version": PYTHON_AUTHORITY_SCHEMA_VERSION,
        "implementation": _require_text(capture.implementation, "Python implementation"),
        "version": _require_version(capture.version, "Python version"),
        "cache_tag": _require_text(capture.cache_tag, "Python cache_tag"),
        "abi_flags": _require_text(capture.abi_flags, "Python abi_flags", allow_empty=True),
        "platform": _require_text(capture.platform, "Python platform"),
        "executable": executable.authority.as_dict(),
        "files": [item.as_dict() for item in files],
        "tree_sha256": tree_sha256,
    }
    authority = PythonRuntimeAuthority(
        implementation=body["implementation"],  # type: ignore[arg-type]
        version=body["version"],  # type: ignore[arg-type]
        cache_tag=body["cache_tag"],  # type: ignore[arg-type]
        abi_flags=body["abi_flags"],  # type: ignore[arg-type]
        platform=body["platform"],  # type: ignore[arg-type]
        executable=executable.authority,
        files=files,
        tree_sha256=tree_sha256,
        identity_sha256=_sha256(canonical_json_bytes(body)),
    )
    return authority, runtime_files


def _build_distribution_authority(
    capture: DistributionCaptureInput,
    *,
    lease: _WindowsClosedTreeLease | None = None,
) -> tuple[DistributionAuthority, tuple[_CapturedFile, ...]]:
    name = normalize_distribution_name(capture.name)
    version = _require_version(capture.version, f"{name} version")
    root = _validate_trusted_root(capture.install_root, f"{name} install root")
    if (
        isinstance(capture.declared_files, (str, bytes))
        or not isinstance(capture.declared_files, Sequence)
        or not capture.declared_files
    ):
        raise ReleaseAuthorityError(f"{name} declared file list is empty or malformed")
    declared_paths = tuple(
        _candidate_within_root(root, path, f"{name} declared file")[1]
        for path in capture.declared_files
    )
    if len(declared_paths) != len(set(declared_paths)):
        raise ReleaseAuthorityError(f"{name} declared file ownership is duplicate")
    captured = _capture_closed_tree(
        root,
        f"{name} closed distribution tree",
        lease=lease,
    )
    relative_paths = tuple(item.authority.relative_path for item in captured)
    if tuple(sorted(declared_paths)) != relative_paths:
        raise ReleaseAuthorityError(
            f"{name} declared inventory differs from its closed distribution tree"
        )
    origin_absolute, origin_relative = _candidate_within_root(
        root,
        capture.import_origin,
        f"{name} import origin",
    )
    if origin_relative not in set(relative_paths):
        raise ReleaseAuthorityError(f"{name} import origin is not a declared file")
    if _path_key(origin_absolute) not in {item.absolute_path_key for item in captured}:
        raise ReleaseAuthorityError(f"{name} import origin ownership drifted")
    files = tuple(
        sorted(
            (item.authority for item in captured),
            key=lambda item: item.relative_path,
        )
    )
    tree_sha256 = _distribution_tree_sha256(files)
    body = {
        "schema_version": DISTRIBUTION_AUTHORITY_SCHEMA_VERSION,
        "name": name,
        "version": version,
        "import_origin": origin_relative,
        "files": [item.as_dict() for item in files],
        "tree_sha256": tree_sha256,
    }
    authority = DistributionAuthority(
        name=name,
        version=version,
        import_origin=origin_relative,
        files=files,
        tree_sha256=tree_sha256,
        authority_sha256=_sha256(canonical_json_bytes(body)),
    )
    return authority, captured


def _segmenter_from_distribution(distribution: DistributionAuthority) -> SegmenterAuthority:
    body = {
        "schema_version": SEGMENTER_AUTHORITY_SCHEMA_VERSION,
        "distribution_name": distribution.name,
        "distribution_version": distribution.version,
        "import_origin": distribution.import_origin,
        "distribution_tree_sha256": distribution.tree_sha256,
        "distribution_authority_sha256": distribution.authority_sha256,
    }
    return SegmenterAuthority(
        distribution_name=distribution.name,
        distribution_version=distribution.version,
        import_origin=distribution.import_origin,
        distribution_tree_sha256=distribution.tree_sha256,
        distribution_authority_sha256=distribution.authority_sha256,
        authority_sha256=_sha256(canonical_json_bytes(body)),
    )


def _normalize_expected_closure(expected: Mapping[str, str]) -> dict[str, str]:
    if not isinstance(expected, Mapping) or not expected:
        raise ReleaseAuthorityError("expected dependency closure must be non-empty")
    normalized: dict[str, str] = {}
    for raw_name, raw_version in expected.items():
        if not isinstance(raw_name, str):
            raise ReleaseAuthorityError("expected distribution names must be text")
        name = normalize_distribution_name(raw_name)
        if name in normalized:
            raise ReleaseAuthorityError("expected dependency closure has duplicate names")
        normalized[name] = _require_version(raw_version, f"expected {name} version")
    return normalized


def _register_ownership(
    captured: _CapturedFile,
    owner: str,
    *,
    paths: dict[str, str],
    identities: dict[tuple[int, int], str],
) -> None:
    existing = paths.get(captured.absolute_path_key)
    if existing is not None:
        raise ReleaseAuthorityError(
            f"duplicate file ownership between {existing} and {owner}"
        )
    paths[captured.absolute_path_key] = owner
    if captured.physical_identity is not None:
        existing = identities.get(captured.physical_identity)
        if existing is not None:
            raise ReleaseAuthorityError(
                f"duplicate physical file ownership between {existing} and {owner}"
            )
        identities[captured.physical_identity] = owner


def capture_runtime_dependency_authority(
    python: PythonCaptureInput,
    distributions: Sequence[DistributionCaptureInput],
    *,
    expected_distributions: Mapping[str, str],
) -> RuntimeDependencyAuthority:
    """Capture only the explicitly supplied dependency closure and files."""

    if not isinstance(python, PythonCaptureInput):
        raise ReleaseAuthorityError("Python capture input is malformed")
    expected = _normalize_expected_closure(expected_distributions)
    if (
        isinstance(distributions, (str, bytes))
        or not isinstance(distributions, Sequence)
        or not distributions
    ):
        raise ReleaseAuthorityError("distribution captures must be a non-empty sequence")
    captures_by_name: dict[str, DistributionCaptureInput] = {}
    for capture in distributions:
        if not isinstance(capture, DistributionCaptureInput):
            raise ReleaseAuthorityError("distribution capture input is malformed")
        name = normalize_distribution_name(capture.name)
        if name in captures_by_name:
            raise ReleaseAuthorityError("distribution capture has duplicate normalized names")
        captures_by_name[name] = capture
    observed_versions = {
        name: _require_version(capture.version, f"{name} version")
        for name, capture in captures_by_name.items()
    }
    if observed_versions != expected:
        raise ReleaseAuthorityError("distribution closure/version differs from authority input")
    if SEGMENTER_DISTRIBUTION not in expected:
        raise ReleaseAuthorityError("dependency closure must contain underthesea")

    with ExitStack() as lease_stack:
        python_root = _validate_trusted_root(
            python.executable_root,
            "Python executable root",
        )
        python_lease = lease_stack.enter_context(
            _WindowsClosedTreeLease(python_root, "Python runtime tree")
        )
        distribution_leases: dict[str, _WindowsClosedTreeLease] = {}
        for name in sorted(captures_by_name):
            capture = captures_by_name[name]
            root = _validate_trusted_root(
                capture.install_root,
                f"{name} install root",
            )
            distribution_leases[name] = lease_stack.enter_context(
                _WindowsClosedTreeLease(
                    root,
                    f"{name} closed distribution tree",
                )
            )

        python_authority, python_files = _build_python_authority(
            python,
            lease=python_lease,
        )
        ownership_paths: dict[str, str] = {}
        ownership_identities: dict[tuple[int, int], str] = {}
        for python_file in python_files:
            _register_ownership(
                python_file,
                "python-runtime",
                paths=ownership_paths,
                identities=ownership_identities,
            )
        built: list[DistributionAuthority] = []
        for name in sorted(captures_by_name):
            authority, captured_files = _build_distribution_authority(
                captures_by_name[name],
                lease=distribution_leases[name],
            )
            for captured_file in captured_files:
                _register_ownership(
                    captured_file,
                    name,
                    paths=ownership_paths,
                    identities=ownership_identities,
                )
            built.append(authority)
        frozen_distributions = tuple(built)
        segmenter_distribution = next(
            item
            for item in frozen_distributions
            if item.name == SEGMENTER_DISTRIBUTION
        )
        segmenter = _segmenter_from_distribution(segmenter_distribution)
        body = {
            "schema_version": RUNTIME_AUTHORITY_SCHEMA_VERSION,
            "python": python_authority.as_dict(),
            "distributions": [item.as_dict() for item in frozen_distributions],
            "segmenter": segmenter.as_dict(),
        }
        result = RuntimeDependencyAuthority(
            python=python_authority,
            distributions=frozen_distributions,
            segmenter=segmenter,
            authority_sha256=_sha256(canonical_json_bytes(body)),
        )
        python_lease.assert_intact()
        for lease in distribution_leases.values():
            lease.assert_intact()
        return result


def _parse_authority_bytes(payload: bytes) -> RuntimeDependencyAuthority:
    try:
        text = payload.decode("utf-8", errors="strict")
        raw = json.loads(
            text,
            object_pairs_hook=_reject_duplicate_keys,
            parse_constant=lambda value: (_ for _ in ()).throw(
                ReleaseAuthorityError(f"non-finite JSON constant: {value}")
            ),
        )
    except (UnicodeDecodeError, json.JSONDecodeError, ReleaseAuthorityError) as exc:
        raise ReleaseAuthorityError("runtime authority is not strict JSON") from exc
    if not isinstance(raw, dict):
        raise ReleaseAuthorityError("runtime authority must be a JSON object")
    if payload != canonical_json_bytes(raw):
        raise ReleaseAuthorityError("runtime authority bytes are noncanonical")
    return RuntimeDependencyAuthority.from_dict(raw)


def load_runtime_dependency_authority(path: Path) -> RuntimeDependencyAuthority:
    """Load one canonical authority without following a link/reparse artifact."""

    candidate = Path(path)
    if not candidate.is_absolute():
        raise ReleaseAuthorityError("runtime authority path must be absolute")
    if not candidate.is_file() or _path_is_redirecting(candidate):
        raise ReleaseAuthorityError("runtime authority is missing or redirecting")
    captured = _capture_regular_file(
        _validate_trusted_root(candidate.parent, "runtime authority parent"),
        candidate,
        "runtime authority",
    )
    payload = candidate.read_bytes()
    if len(payload) != captured.authority.bytes or _sha256(payload) != captured.authority.sha256:
        raise ReleaseAuthorityError("runtime authority changed while being loaded")
    return _parse_authority_bytes(payload)


def write_runtime_dependency_authority(
    path: Path,
    authority: RuntimeDependencyAuthority,
) -> Path:
    """Write a canonical authority once and durably; never replace drifted bytes."""

    if not isinstance(authority, RuntimeDependencyAuthority):
        raise ReleaseAuthorityError("runtime authority object is malformed")
    target = Path(path)
    if not target.is_absolute():
        raise ReleaseAuthorityError("runtime authority path must be absolute")
    parent = _validate_trusted_root(target.parent, "runtime authority parent")
    if _path_key(parent) != _path_key(target.parent):
        raise ReleaseAuthorityError("runtime authority parent path drifted")
    payload = canonical_json_bytes(authority.as_dict())
    if target.exists() or target.is_symlink():
        if target.is_file() and not _path_is_redirecting(target) and target.read_bytes() == payload:
            return target
        raise FileExistsError("refusing to replace runtime dependency authority")
    try:
        with target.open("xb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
    except OSError:
        if target.exists() and target.is_file() and target.read_bytes() == payload:
            return target
        raise
    return target


def verify_runtime_dependency_authority(
    authority_or_path: RuntimeDependencyAuthority | Path,
    python: PythonCaptureInput,
    distributions: Sequence[DistributionCaptureInput],
    *,
    expected_distributions: Mapping[str, str],
) -> RuntimeDependencyAuthority:
    """Recapture explicit roots and require exact equality with the authority."""

    expected = (
        authority_or_path
        if isinstance(authority_or_path, RuntimeDependencyAuthority)
        else load_runtime_dependency_authority(Path(authority_or_path))
    )
    observed = capture_runtime_dependency_authority(
        python,
        distributions,
        expected_distributions=expected_distributions,
    )
    if canonical_json_bytes(expected.as_dict()) != canonical_json_bytes(observed.as_dict()):
        raise ReleaseAuthorityError("runtime dependency authority verification drifted")
    return expected


__all__ = [
    "DISTRIBUTION_AUTHORITY_SCHEMA_VERSION",
    "DistributionAuthority",
    "DistributionCaptureInput",
    "FileAuthority",
    "PYTHON_AUTHORITY_SCHEMA_VERSION",
    "PythonCaptureInput",
    "PythonRuntimeAuthority",
    "RUNTIME_AUTHORITY_FILENAME",
    "RUNTIME_AUTHORITY_SCHEMA_VERSION",
    "ReleaseAuthorityError",
    "RuntimeDependencyAuthority",
    "SEGMENTER_AUTHORITY_SCHEMA_VERSION",
    "SEGMENTER_DISTRIBUTION",
    "SegmenterAuthority",
    "canonical_json_bytes",
    "capture_runtime_dependency_authority",
    "load_runtime_dependency_authority",
    "normalize_distribution_name",
    "verify_runtime_dependency_authority",
    "write_runtime_dependency_authority",
]
