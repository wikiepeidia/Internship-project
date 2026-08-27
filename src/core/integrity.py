"""Forward-only integrity primitives for active application code."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import stat
from typing import Any
import uuid

from src.core_binding import BoundParent, bind_parent


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
    """Best-effort cleanup through a protected parent and exact file handle."""

    target = Path(os.path.abspath(path))
    try:
        parent_identity = _directory_identity(target.parent, where="cleanup parent")
        with bind_parent(target.parent) as parent:
            if not parent.unlink_if_identity(target.name, expected):
                return False
        _require_directory_identity(target.parent, parent_identity, where="cleanup parent")
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


def read_file_bytes(path: Path, *, where: str) -> bytes:
    """Capture bytes from one stable, non-redirecting file descriptor."""

    source = reject_redirecting_ancestry(Path(os.path.abspath(path)), where=where)
    parent_identity = _directory_identity(source.parent, where=f"{where} parent")
    path_identity = _regular_identity(source, where=where)
    flags = os.O_RDONLY | int(getattr(os, "O_BINARY", 0))
    flags |= int(getattr(os, "O_NOFOLLOW", 0))
    try:
        descriptor = os.open(source, flags)
    except OSError as error:
        raise IntegrityError(f"cannot open {where} without following redirects") from error
    with os.fdopen(descriptor, "rb") as handle:
        if _identity(os.fstat(handle.fileno())) != path_identity:
            raise IntegrityError(f"{where} descriptor does not match the inspected file")
        value = handle.read()
        if _identity(os.fstat(handle.fileno())) != path_identity:
            raise IntegrityError(f"{where} changed while reading")
    _require_identity(source, path_identity, where=where)
    _require_directory_identity(source.parent, parent_identity, where=f"{where} parent")
    return value


def _artifact_inventory(root: Path, current: Path) -> list[tuple[str, tuple[int, int, int, int, int]]]:
    metadata = os.lstat(current)
    if _is_redirecting(current):
        raise IntegrityError("model artifact must not contain redirects")
    if stat.S_ISREG(metadata.st_mode):
        return [(current.relative_to(root).as_posix(), _identity(metadata))]
    if not stat.S_ISDIR(metadata.st_mode):
        raise IntegrityError("model artifact may contain only directories and regular files")
    result: list[tuple[str, tuple[int, int, int, int, int]]] = []
    for name in sorted(os.listdir(current)):
        result.extend(_artifact_inventory(root, current / name))
    return result


def artifact_digest(path: Path) -> tuple[str, int, int]:
    """Hash one regular file or an exact redirect-free directory tree."""

    candidate = reject_redirecting_ancestry(
        Path(os.path.abspath(path)), where="model artifact"
    )
    metadata = os.lstat(candidate)
    if stat.S_ISREG(metadata.st_mode):
        identity = _identity(metadata)
        digest = sha256_file(candidate)
        _require_identity(candidate, identity, where="model artifact")
        return digest, 1, identity[3]
    if not stat.S_ISDIR(metadata.st_mode):
        raise IntegrityError("model artifact must be a regular file or directory")
    before = _artifact_inventory(candidate, candidate)
    if not before:
        raise IntegrityError("model artifact directory must not be empty")
    entries: list[dict[str, object]] = []
    for relative, identity in before:
        source = candidate / Path(relative)
        digest = sha256_file(source)
        _require_identity(source, identity, where="model artifact member")
        entries.append({"path": relative, "bytes": identity[3], "sha256": digest})
    if _artifact_inventory(candidate, candidate) != before:
        raise IntegrityError("model artifact tree changed while hashing")
    payload = {"schema_version": "model-artifact-tree-v1", "files": entries}
    return sha256_bytes(canonical_json_bytes(payload)), len(entries), sum(
        int(entry["bytes"]) for entry in entries
    )


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

    raw = read_file_bytes(Path(path), where=where)

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
    identities: dict[Path, tuple[tuple[int, int, int, int, int], bool]] = {}
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
        identities[component] = (_identity(metadata), stat.S_ISDIR(metadata.st_mode))
    for component, (expected, is_directory) in identities.items():
        if is_directory:
            _require_directory_identity(
                component,
                expected,
                where=f"{where} ancestry component",
            )
        else:
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


def prepare_bounded_output(root: Path, relative: Path, *, where: str) -> Path:
    """Create only missing parent directories below one trusted root."""

    trusted_root = reject_redirecting_ancestry(Path(root), where=f"{where} root")
    root_identity = _directory_identity(trusted_root, where=f"{where} root")
    target = bounded_descendant(trusted_root, relative, where=where)
    supplied = Path(relative)
    current = trusted_root
    for part in supplied.parent.parts:
        current = current / part
        try:
            metadata = os.lstat(current)
        except FileNotFoundError:
            try:
                current.mkdir()
            except FileExistsError:
                pass
            metadata = os.lstat(current)
        if _is_redirecting(current) or not stat.S_ISDIR(metadata.st_mode):
            raise IntegrityError(f"{where} parent must be a non-redirecting directory")
    _require_directory_identity(trusted_root, root_identity, where=f"{where} root")
    return bounded_descendant(trusted_root, supplied, where=where)


def _output_path(path: Path, *, where: str) -> Path:
    target = reject_redirecting_ancestry(Path(path), where=where)
    parent = reject_redirecting_ancestry(target.parent, where=f"{where} parent")
    if not parent.is_dir():
        raise IntegrityError(f"{where} parent must be an existing directory")
    return target


def _bound_output(
    path: Path,
    *,
    where: str,
) -> tuple[Path, BoundParent, tuple[int, int, int, int, int], Any]:
    """Enter a protected parent binding for one validated output pathname."""

    target = _output_path(path, where=where)
    parent_identity = _directory_identity(target.parent, where=f"{where} parent")
    manager = bind_parent(target.parent)
    try:
        parent = manager.__enter__()
    except OSError as exc:
        raise IntegrityError(f"cannot bind {where} parent safely") from exc
    try:
        _require_directory_identity(target.parent, parent_identity, where=f"{where} parent")
    except Exception:
        manager.__exit__(*__import__("sys").exc_info())
        raise
    return target, parent, parent_identity, manager


def _bound_bytes(
    parent: BoundParent,
    name: str,
    expected: tuple[int, int, int, int, int],
    *,
    where: str,
) -> bytes:
    flags = os.O_RDONLY | int(getattr(os, "O_BINARY", 0))
    flags |= int(getattr(os, "O_NOFOLLOW", 0))
    descriptor = parent.open(name, flags)
    with os.fdopen(descriptor, "rb") as handle:
        if _identity(os.fstat(handle.fileno())) != expected:
            raise IntegrityError(f"{where} descriptor identity changed")
        value = handle.read()
        if _identity(os.fstat(handle.fileno())) != expected:
            raise IntegrityError(f"{where} changed while reading")
    if _identity(parent.lstat(name)) != expected:
        raise IntegrityError(f"{where} pathname identity changed")
    return value


def _bound_temporary(parent: BoundParent, target_name: str) -> tuple[int, str]:
    flags = os.O_CREAT | os.O_EXCL | os.O_RDWR | int(getattr(os, "O_BINARY", 0))
    for _attempt in range(128):
        name = f".{target_name}.{uuid.uuid4().hex}.tmp"
        try:
            return parent.open(name, flags), name
        except FileExistsError:
            continue
    raise IntegrityError("could not allocate a collision-free staging name")


def write_bytes_exclusive(path: Path, value: bytes, *, where: str = "artifact") -> Path:
    """Create one artifact exclusively and verify its owned identity and bytes."""

    target, parent, parent_identity, binding = _bound_output(path, where=where)
    created_identity: tuple[int, int, int, int, int] | None = None
    try:
        flags = os.O_CREAT | os.O_EXCL | os.O_RDWR | int(getattr(os, "O_BINARY", 0))
        descriptor = parent.open(target.name, flags, 0o600)
        with os.fdopen(descriptor, "w+b") as handle:
            handle.write(value)
            handle.flush()
            os.fsync(handle.fileno())
            created_identity = _identity(os.fstat(handle.fileno()))
            handle.seek(0)
            if handle.read() != value:
                raise IntegrityError(f"{where} bytes changed during exclusive write")
        if _identity(parent.lstat(target.name)) != created_identity:
            raise IntegrityError(f"{where} pathname identity changed")
        _require_directory_identity(target.parent, parent_identity, where=f"{where} parent")
        if sha256_bytes(_bound_bytes(parent, target.name, created_identity, where=where)) != sha256_bytes(value):
            raise IntegrityError(f"{where} bytes changed during exclusive write")
    except FileExistsError as exc:
        raise IntegrityError(f"{where} already exists: {target}") from exc
    except Exception:
        if created_identity is not None:
            parent.unlink_if_identity(target.name, created_identity)
        raise
    finally:
        binding.__exit__(None, None, None)
    return target


def atomic_replace_new_artifact(
    path: Path,
    value: bytes,
    *,
    where: str = "artifact",
) -> Path:
    """Publish complete bytes atomically while refusing target replacement."""

    target, parent, parent_identity, binding = _bound_output(path, where=where)
    try:
        descriptor, temporary_name = _bound_temporary(parent, target.name)
    except Exception:
        binding.__exit__(*__import__("sys").exc_info())
        raise
    temporary_identity = _identity(os.fstat(descriptor))
    published = False
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(value)
            handle.flush()
            os.fsync(handle.fileno())
            temporary_identity = _identity(os.fstat(handle.fileno()))
        if _identity(parent.lstat(temporary_name)) != temporary_identity:
            raise IntegrityError(f"{where} temporary identity changed")
        _require_directory_identity(target.parent, parent_identity, where=f"{where} parent")
        try:
            parent.link(temporary_name, target.name)
            published = True
        except FileExistsError as exc:
            raise IntegrityError(f"{where} already exists: {target}") from exc
        except OSError as exc:
            raise IntegrityError(f"{where} could not be published atomically") from exc
        if _identity(parent.lstat(target.name)) != temporary_identity:
            raise IntegrityError(f"{where} pathname identity changed")
        _require_directory_identity(target.parent, parent_identity, where=f"{where} parent")
        if sha256_bytes(_bound_bytes(parent, target.name, temporary_identity, where=where)) != sha256_bytes(value):
            raise IntegrityError(f"{where} bytes changed during atomic publication")
    except Exception:
        if published:
            parent.unlink_if_identity(target.name, temporary_identity)
        raise
    finally:
        parent.unlink_if_identity(temporary_name, temporary_identity)
        binding.__exit__(None, None, None)
    return target


def atomic_replace_artifact(
    path: Path,
    value: bytes,
    *,
    where: str = "artifact",
) -> Path:
    """Replace one artifact from a verified, identity-owned staging file."""

    target, parent, parent_identity, binding = _bound_output(path, where=where)
    try:
        descriptor, temporary_name = _bound_temporary(parent, target.name)
    except Exception:
        binding.__exit__(*__import__("sys").exc_info())
        raise
    temporary_identity = _identity(os.fstat(descriptor))
    published = False
    try:
        with os.fdopen(descriptor, "w+b") as handle:
            handle.write(value)
            handle.flush()
            os.fsync(handle.fileno())
            temporary_identity = _identity(os.fstat(handle.fileno()))
            handle.seek(0)
            if handle.read() != value:
                raise IntegrityError(f"{where} staging bytes changed")
        if _identity(parent.lstat(temporary_name)) != temporary_identity:
            raise IntegrityError(f"{where} staging identity changed")
        _require_directory_identity(target.parent, parent_identity, where=f"{where} parent")
        parent.replace(temporary_name, target.name)
        published = True
        if _identity(parent.lstat(target.name)) != temporary_identity:
            raise IntegrityError(f"{where} pathname identity changed")
        _require_directory_identity(target.parent, parent_identity, where=f"{where} parent")
        if _bound_bytes(parent, target.name, temporary_identity, where=where) != value:
            raise IntegrityError(f"{where} bytes changed during replacement")
    finally:
        if not published:
            parent.unlink_if_identity(temporary_name, temporary_identity)
        binding.__exit__(None, None, None)
    return target
