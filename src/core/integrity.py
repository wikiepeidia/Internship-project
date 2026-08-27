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


def sha256_bytes(value: bytes) -> str:
    """Return the lowercase SHA-256 identity of captured bytes."""

    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    """Return the lowercase SHA-256 identity of one regular file."""

    source = Path(path)
    if not source.is_file():
        raise FileNotFoundError(f"Missing artifact file: {source}")
    digest = hashlib.sha256()
    with source.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
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
    for component in reversed((candidate, *candidate.parents)):
        try:
            redirecting = _is_redirecting(component)
        except FileNotFoundError:
            continue
        except OSError as exc:
            raise IntegrityError(f"cannot inspect {where} safely: {component}") from exc
        if redirecting:
            raise IntegrityError(f"{where} ancestry must not contain a symlink or reparse point")
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
    """Create one artifact exclusively and verify its captured bytes."""

    target = _output_path(path, where=where)
    created = False
    try:
        with target.open("xb") as handle:
            created = True
            handle.write(value)
            handle.flush()
            os.fsync(handle.fileno())
        if sha256_file(target) != sha256_bytes(value):
            raise IntegrityError(f"{where} bytes changed during exclusive write")
    except FileExistsError as exc:
        raise IntegrityError(f"{where} already exists: {target}") from exc
    except Exception:
        if created:
            target.unlink(missing_ok=True)
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
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{target.name}.",
        suffix=".tmp",
        dir=target.parent,
    )
    temporary = Path(temporary_name)
    published = False
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(value)
            handle.flush()
            os.fsync(handle.fileno())
        reject_redirecting_ancestry(temporary, where=f"{where} temporary file")
        try:
            os.link(temporary, target, follow_symlinks=False)
            published = True
        except FileExistsError as exc:
            raise IntegrityError(f"{where} already exists: {target}") from exc
        except OSError as exc:
            raise IntegrityError(f"{where} could not be published atomically") from exc
        if sha256_file(target) != sha256_bytes(value):
            raise IntegrityError(f"{where} bytes changed during atomic publication")
    except Exception:
        if published:
            target.unlink(missing_ok=True)
        raise
    finally:
        temporary.unlink(missing_ok=True)
    return target
