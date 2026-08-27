"""Forward-only integrity primitives for active application code."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import stat
import tempfile
from typing import Any


_WINDOWS_REPARSE_POINT = 0x400


class IntegrityError(RuntimeError):
    """Raised when untrusted bytes fail an integrity boundary."""


def _identity(metadata: os.stat_result) -> tuple[int, int, int, int, int]:
    return (
        metadata.st_dev,
        metadata.st_ino,
        metadata.st_mode,
        metadata.st_size,
        metadata.st_mtime_ns,
    )


def _regular_identity(path: Path, *, where: str) -> tuple[int, int, int, int, int]:
    try:
        metadata = os.lstat(path)
    except FileNotFoundError as error:
        raise FileNotFoundError(f"Missing artifact file: {path}") from error
    if _is_redirecting(path) or not stat.S_ISREG(metadata.st_mode):
        raise IntegrityError(f"{where} must be a non-redirecting regular file")
    return _identity(metadata)


def _directory_identity(path: Path, *, where: str) -> tuple[int, int, int, int, int]:
    metadata = os.lstat(path)
    if _is_redirecting(path) or not stat.S_ISDIR(metadata.st_mode):
        raise IntegrityError(f"{where} must be a non-redirecting directory")
    return _identity(metadata)


def _require_identity(
    path: Path,
    expected: tuple[int, int, int, int, int],
    *,
    where: str,
) -> None:
    try:
        actual = _identity(os.lstat(path))
    except FileNotFoundError as error:
        raise IntegrityError(f"{where} disappeared during the operation") from error
    if actual != expected:
        raise IntegrityError(f"{where} identity changed during the operation")


def _require_directory_identity(
    path: Path,
    expected: tuple[int, int, int, int, int],
    *,
    where: str,
) -> None:
    try:
        actual = _identity(os.lstat(path))
    except FileNotFoundError as error:
        raise IntegrityError(f"{where} disappeared during the operation") from error
    if actual[:3] != expected[:3]:
        raise IntegrityError(f"{where} identity changed during the operation")


def _unlink_if_owned(path: Path, expected: tuple[int, int, int, int, int]) -> bool:
    """Best-effort cleanup that never unlinks an already-different object."""

    try:
        if _identity(os.lstat(path)) != expected:
            return False
        path.unlink()
        return True
    except FileNotFoundError:
        return False


def sha256_bytes(value: bytes) -> str:
    """Return the lowercase SHA-256 identity of captured bytes."""

    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    """Hash one stable, non-redirecting regular-file descriptor."""

    source = reject_redirecting_ancestry(
        Path(os.path.abspath(path)), where="artifact file"
    )
    parent_identity = _directory_identity(source.parent, where="artifact parent")
    path_identity = _regular_identity(source, where="artifact file")
    flags = os.O_RDONLY | int(getattr(os, "O_BINARY", 0))
    flags |= int(getattr(os, "O_NOFOLLOW", 0))
    try:
        descriptor = os.open(source, flags)
    except OSError as error:
        raise IntegrityError(f"cannot open artifact without following redirects: {source}") from error
    digest = hashlib.sha256()
    with os.fdopen(descriptor, "rb") as handle:
        if _identity(os.fstat(handle.fileno())) != path_identity:
            raise IntegrityError("artifact descriptor does not match the inspected file")
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
        if _identity(os.fstat(handle.fileno())) != path_identity:
            raise IntegrityError("artifact file changed while hashing")
    _require_identity(source, path_identity, where="artifact file")
    _require_directory_identity(source.parent, parent_identity, where="artifact parent")
    return digest.hexdigest()


def canonical_json_bytes(value: Any) -> bytes:
    """Serialize a JSON-compatible value as compact UTF-8 plus one LF."""

    return (
        json.dumps(
            value,
            ensure_ascii=False,
            separators=(",", ":"),
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")


def strict_json_object(path: Path, *, where: str) -> dict[str, Any]:
    """Read one strict UTF-8 JSON object while rejecting duplicate keys."""

    raw = Path(path).read_bytes()

    def reject_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise IntegrityError(f"{where} contains duplicate JSON key {key!r}")
            result[key] = value
        return result

    def reject_non_finite(token: str) -> Any:
        raise IntegrityError(f"{where} contains non-standard JSON token {token!r}")

    try:
        value = json.loads(
            raw.decode("utf-8", errors="strict"),
            object_pairs_hook=reject_duplicates,
            parse_constant=reject_non_finite,
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise IntegrityError(f"{where} must be strict UTF-8 JSON") from exc
    if not isinstance(value, dict):
        raise IntegrityError(f"{where} must be a JSON object")
    return value


def _absolute(path: Path) -> Path:
    return Path(os.path.abspath(os.path.normpath(os.fspath(path))))


def _is_redirecting(path: Path) -> bool:
    metadata = os.lstat(path)
    return bool(
        stat.S_ISLNK(metadata.st_mode)
        or int(getattr(metadata, "st_file_attributes", 0))
        & _WINDOWS_REPARSE_POINT
    )


def reject_redirecting_ancestry(path: Path, *, where: str) -> Path:
    """Reject symlink or reparse components in an absolute path's ancestry."""

    supplied = Path(path)
    raw = os.fspath(supplied)
    if not supplied.is_absolute() or "\x00" in raw or ".." in supplied.parts:
        raise IntegrityError(f"{where} must be a canonical absolute path")
    candidate = _absolute(supplied)
    identities: dict[Path, tuple[int, int, int, int, int]] = {}
    for component in reversed((candidate, *candidate.parents)):
        try:
            metadata = os.lstat(component)
            redirecting = _is_redirecting(component)
        except FileNotFoundError:
            continue
        except OSError as exc:
            raise IntegrityError(f"cannot inspect {where} safely: {component}") from exc
        if redirecting:
            raise IntegrityError(f"{where} ancestry must not contain a symlink or reparse point")
        identities[component] = _identity(metadata)
    for component, expected in identities.items():
        _require_identity(component, expected, where=f"{where} ancestry component")
    return candidate


def bounded_descendant(root: Path, relative: Path, *, where: str) -> Path:
    """Return one non-redirecting relative descendant of an existing root."""

    trusted_root = reject_redirecting_ancestry(Path(root), where=f"{where} root")
    if trusted_root.parent == trusted_root or not trusted_root.is_dir():
        raise IntegrityError(f"{where} root must be an existing bounded directory")
    supplied = Path(relative)
    raw = os.fspath(supplied)
    if supplied.is_absolute() or "\x00" in raw or ".." in supplied.parts:
        raise IntegrityError(f"{where} path must be bounded and relative")
    candidate = _absolute(trusted_root / supplied)
    if candidate == trusted_root or trusted_root not in candidate.parents:
        raise IntegrityError(f"{where} path escaped its root")
    return reject_redirecting_ancestry(candidate, where=where)


def _output_path(path: Path, *, where: str) -> Path:
    target = reject_redirecting_ancestry(Path(path), where=where)
    parent = reject_redirecting_ancestry(target.parent, where=f"{where} parent")
    if not parent.is_dir():
        raise IntegrityError(f"{where} parent must be an existing directory")
    return target


def write_bytes_exclusive(path: Path, value: bytes, *, where: str = "artifact") -> Path:
    """Create one artifact exclusively and verify its owned identity and bytes."""

    target = _output_path(path, where=where)
    parent_identity = _directory_identity(target.parent, where=f"{where} parent")
    created_identity: tuple[int, int, int, int, int] | None = None
    try:
        flags = os.O_CREAT | os.O_EXCL | os.O_RDWR | int(getattr(os, "O_BINARY", 0))
        descriptor = os.open(target, flags, 0o600)
        with os.fdopen(descriptor, "w+b") as handle:
            handle.write(value)
            handle.flush()
            os.fsync(handle.fileno())
            created_identity = _identity(os.fstat(handle.fileno()))
            handle.seek(0)
            if handle.read() != value:
                raise IntegrityError(f"{where} bytes changed during exclusive write")
        _require_identity(target, created_identity, where=where)
        _require_directory_identity(target.parent, parent_identity, where=f"{where} parent")
        if sha256_file(target) != sha256_bytes(value):
            raise IntegrityError(f"{where} bytes changed during exclusive write")
    except FileExistsError as exc:
        raise IntegrityError(f"{where} already exists: {target}") from exc
    except Exception:
        if created_identity is not None:
            _unlink_if_owned(target, created_identity)
        raise
    return target


def atomic_replace_new_artifact(
    path: Path,
    value: bytes,
    *,
    where: str = "artifact",
) -> Path:
    """Publish complete bytes atomically while refusing target replacement."""

    target = _output_path(path, where=where)
    parent_identity = _directory_identity(target.parent, where=f"{where} parent")
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{target.name}.",
        suffix=".tmp",
        dir=target.parent,
    )
    temporary = Path(temporary_name)
    temporary_identity = _identity(os.fstat(descriptor))
    published = False
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(value)
            handle.flush()
            os.fsync(handle.fileno())
            temporary_identity = _identity(os.fstat(handle.fileno()))
        reject_redirecting_ancestry(temporary, where=f"{where} temporary file")
        _require_directory_identity(target.parent, parent_identity, where=f"{where} parent")
        try:
            os.link(temporary, target, follow_symlinks=False)
            published = True
        except FileExistsError as exc:
            raise IntegrityError(f"{where} already exists: {target}") from exc
        except OSError as exc:
            raise IntegrityError(f"{where} could not be published atomically") from exc
        _require_identity(target, temporary_identity, where=where)
        _require_directory_identity(target.parent, parent_identity, where=f"{where} parent")
        if sha256_file(target) != sha256_bytes(value):
            raise IntegrityError(f"{where} bytes changed during atomic publication")
    except Exception:
        if published:
            _unlink_if_owned(target, temporary_identity)
        raise
    finally:
        _unlink_if_owned(temporary, temporary_identity)
    return target
