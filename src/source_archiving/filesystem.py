"""Bound filesystem operations for source-closure publication."""

from __future__ import annotations

from contextlib import ExitStack
import os
from pathlib import Path, PurePosixPath
import stat
from typing import Callable, Mapping

from src.core_binding import BoundParent, bind_parent

from .contracts import (
    ArchiveError,
    MANIFEST_ARCHIVE_NAME,
    RECEIPT_ARCHIVE_NAME,
    TREE_ARCHIVE_NAME,
    _bounded_relative,
    _sha256,
)


_WINDOWS_REPARSE_POINT = 0x00000400
PublicationHook = Callable[[str, Path], None]


def _absolute(path: Path) -> Path:
    return Path(os.path.abspath(os.path.normpath(os.fspath(path))))


def _redirecting(metadata: os.stat_result) -> bool:
    return bool(
        stat.S_ISLNK(metadata.st_mode)
        or int(getattr(metadata, "st_file_attributes", 0)) & _WINDOWS_REPARSE_POINT
    )


def _validate_ancestry(
    root: Path,
    target: Path,
    *,
    target_file: bool,
    where: str,
) -> None:
    root_abs, target_abs = _absolute(root), _absolute(target)
    try:
        common = Path(os.path.commonpath((os.fspath(root_abs), os.fspath(target_abs))))
    except ValueError as exc:
        raise ArchiveError(f"{where} escaped its fixed evidence root") from exc
    if common != root_abs or target_abs == root_abs:
        raise ArchiveError(f"{where} escaped its fixed evidence root")
    components = [root_abs]
    relative = target_abs.relative_to(root_abs)
    current = root_abs
    for part in relative.parts:
        current /= part
        components.append(current)
    for component in components:
        try:
            metadata = os.lstat(component)
        except OSError as exc:
            raise ArchiveError(f"{where} is missing") from exc
        if _redirecting(metadata):
            raise ArchiveError(f"{where} ancestry contains a symlink or reparse point")
    final = os.lstat(target_abs)
    if target_file and not stat.S_ISREG(final.st_mode):
        raise ArchiveError(f"{where} must be a regular file")
    if not target_file and not stat.S_ISDIR(final.st_mode):
        raise ArchiveError(f"{where} must be a directory")


def _validate_output_destination(path: Path) -> Path:
    supplied = Path(path)
    if not supplied.is_absolute() or ".." in supplied.parts or "\x00" in os.fspath(supplied):
        raise ArchiveError("archive destination must be canonical and absolute")
    destination = _absolute(supplied)
    parent = destination.parent
    if os.path.lexists(destination):
        raise ArchiveError("archive destination already exists; collision refused")
    for component in reversed((parent, *parent.parents)):
        try:
            metadata = os.lstat(component)
        except OSError as exc:
            raise ArchiveError("archive destination parent is missing") from exc
        if _redirecting(metadata):
            raise ArchiveError(
                "archive destination ancestry contains a symlink or reparse point"
            )
    if not stat.S_ISDIR(os.lstat(parent).st_mode):
        raise ArchiveError("archive destination parent must be a directory")
    return destination


def _publication_test_hook(event: str, path: Path) -> None:
    """Deterministic race-test seam; production publication leaves it inert."""


class _PublicationBinding:
    """Bind one archive publication to protected destination directory handles."""

    def __init__(
        self,
        destination: Path,
        staging: Path,
        publication_test_hook: PublicationHook = _publication_test_hook,
    ) -> None:
        self.destination = _validate_output_destination(destination)
        self.staging = _validate_output_destination(staging)
        if self.destination.parent != self.staging.parent:
            raise ArchiveError("archive staging must share the destination parent")
        self.parent = self.destination.parent
        self._publication_test_hook = publication_test_hook
        self._stack = ExitStack()
        self._tree_stack = ExitStack()
        self._parent_binding: BoundParent | None = None
        self._directories: dict[tuple[str, ...], BoundParent] = {}

    def __enter__(self) -> _PublicationBinding:
        try:
            self._parent_binding = self._stack.enter_context(bind_parent(self.parent))
        except OSError as exc:
            raise ArchiveError("cannot bind archive destination parent") from exc
        self._assert_parent_binding()
        return self

    def __exit__(self, *_exc: object) -> None:
        self.close()

    def close(self) -> None:
        self._tree_stack.close()
        self._stack.close()
        self._directories.clear()
        self._parent_binding = None

    def _assert_parent_binding(self) -> None:
        if self._parent_binding is None:
            raise ArchiveError("archive destination parent is not protected")
        try:
            self._parent_binding.assert_still_named()
        except OSError as exc:
            raise ArchiveError("archive destination parent binding changed") from exc

    def create_staging(self) -> None:
        self._publication_test_hook("stage_creation", self.staging)
        self._assert_parent_binding()
        if self._parent_binding is None:
            raise ArchiveError("archive destination parent is not protected")
        try:
            stage = self._tree_stack.enter_context(
                self._parent_binding.bind_child_directory(self.staging.name, create=True)
            )
        except OSError as exc:
            raise ArchiveError("archive staging collision during publication") from exc
        self._directories[()] = stage
        self._assert_parent_binding()

    def _directory_handle(self, parts: tuple[str, ...]) -> BoundParent:
        if () not in self._directories:
            raise ArchiveError("archive staging handle is unavailable")
        current_parts: tuple[str, ...] = ()
        binding = self._directories[()]
        for name in parts:
            current_parts += (name,)
            cached = self._directories.get(current_parts)
            if cached is not None:
                binding = cached
                continue
            try:
                binding = self._tree_stack.enter_context(
                    binding.bind_child_directory(name, create=True)
                )
            except OSError as exc:
                raise ArchiveError("cannot create archive member directory") from exc
            self._directories[current_parts] = binding
        return binding

    def write_exclusive(self, relative: Path, raw: bytes) -> None:
        bounded = _bounded_relative(relative.as_posix(), where="archive member")
        parts = tuple(PurePosixPath(bounded).parts)
        if not parts:
            raise ArchiveError("archive member path is empty")
        parent_binding = self._directory_handle(parts[:-1])
        target = self.staging.joinpath(*parts)
        self._publication_test_hook("member_write", target)
        self._assert_parent_binding()
        flags = (
            os.O_RDWR
            | os.O_CREAT
            | os.O_EXCL
            | getattr(os, "O_BINARY", 0)
            | getattr(os, "O_NOFOLLOW", 0)
        )
        try:
            descriptor = parent_binding.open(parts[-1], flags, 0o600)
        except OSError as exc:
            raise ArchiveError(f"exclusive archive write failed: {parts[-1]}") from exc
        try:
            metadata = os.fstat(descriptor)
            if not stat.S_ISREG(metadata.st_mode):
                raise ArchiveError("exclusive archive target is not a regular file")
            view = memoryview(raw)
            while view:
                written = os.write(descriptor, view)
                if written <= 0:
                    raise ArchiveError("exclusive archive write made no progress")
                view = view[written:]
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
        after = parent_binding.lstat(parts[-1])
        if _redirecting(after) or (after.st_dev, after.st_ino) != (
            metadata.st_dev,
            metadata.st_ino,
        ):
            raise ArchiveError("exclusive archive target changed identity")
        self._assert_parent_binding()

    def publish(self) -> None:
        self._publication_test_hook("final_rename", self.destination)
        self._assert_parent_binding()
        if self._parent_binding is None or () not in self._directories:
            raise ArchiveError("archive publication handles are unavailable")
        stage_identity = self._directories[()].directory_identity()
        self._tree_stack.close()
        self._directories.clear()
        try:
            self._parent_binding.rename_noreplace(
                self.staging.name,
                self.destination.name,
                expected_identity=stage_identity,
            )
            with self._parent_binding.bind_child_directory(
                self.destination.name
            ) as published:
                published_identity = published.directory_identity()
        except OSError as exc:
            raise ArchiveError("protected archive rename failed") from exc
        if published_identity != stage_identity:
            raise ArchiveError("published archive handle does not bind the destination")
        self._assert_parent_binding()


def _paths_overlap(first: Path, second: Path) -> bool:
    first_abs, second_abs = _absolute(first), _absolute(second)
    try:
        common = Path(os.path.commonpath((os.fspath(first_abs), os.fspath(second_abs))))
    except ValueError:
        return False
    return common in {first_abs, second_abs}


def _capture_file(path: Path, record: Mapping[str, object], *, where: str) -> bytes:
    before = os.lstat(path)
    if _redirecting(before) or not stat.S_ISREG(before.st_mode):
        raise ArchiveError(f"{where} must be a non-redirecting regular file")
    flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(path, flags)
    except OSError as exc:
        raise ArchiveError(f"cannot capture {where}") from exc
    try:
        chunks: list[bytes] = []
        while True:
            chunk = os.read(descriptor, 1024 * 1024)
            if not chunk:
                break
            chunks.append(chunk)
        after = os.fstat(descriptor)
    finally:
        os.close(descriptor)
    if (before.st_dev, before.st_ino) != (after.st_dev, after.st_ino):
        raise ArchiveError(f"{where} changed identity during capture")
    raw = b"".join(chunks)
    if len(raw) != record["bytes"]:
        raise ArchiveError(f"{where} bytes/hash do not match the manifest")
    if _sha256(raw) != record["sha256"]:
        raise ArchiveError(f"{where} hash does not match the manifest")
    return raw


def _write_exclusive(
    binding: _PublicationBinding,
    relative: Path,
    raw: bytes,
) -> None:
    """Write through the publication's already-held staging-tree handles."""

    binding.write_exclusive(relative, raw)


def _scan_exact_tree(root: Path) -> tuple[set[str], set[str]]:
    root_metadata = os.lstat(root)
    if _redirecting(root_metadata) or not stat.S_ISDIR(root_metadata.st_mode):
        raise ArchiveError("archived tree root must be a non-redirecting directory")
    files: set[str] = set()
    directories: set[str] = set()

    def visit(directory: Path, relative: PurePosixPath) -> None:
        try:
            entries = tuple(os.scandir(directory))
        except OSError as exc:
            raise ArchiveError("cannot enumerate archived tree safely") from exc
        for entry in entries:
            child_relative = relative / entry.name
            child_name = child_relative.as_posix()
            metadata = entry.stat(follow_symlinks=False)
            if _redirecting(metadata):
                raise ArchiveError("archived tree contains a link or reparse member")
            if stat.S_ISDIR(metadata.st_mode):
                directories.add(child_name)
                visit(Path(entry.path), child_relative)
            elif stat.S_ISREG(metadata.st_mode):
                files.add(child_name)
            else:
                raise ArchiveError("archived tree contains a non-file member")

    visit(root, PurePosixPath())
    return files, directories


def _verify_archive_root_members(destination: Path) -> None:
    expected = {
        MANIFEST_ARCHIVE_NAME: "file",
        TREE_ARCHIVE_NAME: "directory",
        RECEIPT_ARCHIVE_NAME: "file",
    }
    actual: dict[str, str] = {}
    for entry in os.scandir(destination):
        metadata = entry.stat(follow_symlinks=False)
        if _redirecting(metadata):
            raise ArchiveError("archive root contains a link or reparse member")
        if stat.S_ISREG(metadata.st_mode):
            actual[entry.name] = "file"
        elif stat.S_ISDIR(metadata.st_mode):
            actual[entry.name] = "directory"
        else:
            raise ArchiveError("archive root contains a non-file member")
    if actual != expected:
        raise ArchiveError("archive root membership is not exact")
