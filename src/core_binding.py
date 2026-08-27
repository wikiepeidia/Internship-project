"""Stable parent-directory bindings for integrity-sensitive publication."""

from __future__ import annotations

from contextlib import contextmanager
import os
from pathlib import Path
import stat
from typing import Iterator
_WINDOWS_REPARSE_POINT = 0x400

def _before_owned_handle_delete(_path: Path) -> None:
    """Deterministic race-test seam immediately before handle-bound deletion."""


def _identity(metadata: os.stat_result) -> tuple[int, int, int, int, int]:
    return (
        metadata.st_dev,
        metadata.st_ino,
        metadata.st_mode,
        metadata.st_size,
        metadata.st_mtime_ns,
    )


class BoundParent:
    """An open parent directory used for all operations on one child name."""

    def __init__(
        self,
        parent: Path,
        *,
        directory_fd: int | None = None,
        windows_handles: tuple[int, ...] = (),
    ) -> None:
        self.parent = parent
        self.directory_fd = directory_fd
        self.windows_handles = windows_handles

    def child(self, name: str) -> Path:
        if not name or name in {".", ".."} or Path(name).name != name:
            raise ValueError("bound child name must be one plain path component")
        return self.parent / name
    def directory_identity(self) -> tuple[int, int]:
        """Return a stable identity for the held directory itself."""
        if self.directory_fd is not None:
            metadata = os.fstat(self.directory_fd)
            identity = (metadata.st_dev, metadata.st_ino)
        elif self.windows_handles:
            _attributes, volume, index = _windows_handle_identity(
                self.windows_handles[-1]
            )
            identity = (volume, index)
        else:
            metadata = os.lstat(self.parent)
            identity = (metadata.st_dev, metadata.st_ino)
        return identity

    def assert_still_named(self) -> None:
        """Fail if the held directory is no longer at its original pathname."""
        metadata = os.lstat(self.parent)
        redirecting = stat.S_ISLNK(metadata.st_mode) or int(
            getattr(metadata, "st_file_attributes", 0)
        ) & _WINDOWS_REPARSE_POINT
        if redirecting:
            raise OSError("bound directory pathname became redirecting")
        if self.directory_fd is not None:
            held = os.fstat(self.directory_fd)
            identity = (held.st_dev, held.st_ino)
        elif self.windows_handles and metadata.st_ino:
            _attributes, _volume, inode = _windows_handle_identity(
                self.windows_handles[-1]
            )
            identity = (metadata.st_dev, inode)
        else:
            identity = (metadata.st_dev, metadata.st_ino)
        if (metadata.st_dev, metadata.st_ino) != identity:
            raise OSError("bound directory pathname changed identity")
    def open(self, name: str, flags: int, mode: int = 0o600) -> int:
        if self.directory_fd is not None:
            return os.open(name, flags, mode, dir_fd=self.directory_fd)
        if self.windows_handles:
            return _windows_open_relative(self.windows_handles[-1], name, flags)
        return os.open(self.child(name), flags, mode)

    def lstat(self, name: str) -> os.stat_result:
        if self.directory_fd is not None:
            return os.stat(name, dir_fd=self.directory_fd, follow_symlinks=False)
        if self.windows_handles:
            descriptor = _windows_open_relative(
                self.windows_handles[-1], name, os.O_RDONLY
            )
            try:
                return os.fstat(descriptor)
            finally:
                os.close(descriptor)
        return os.lstat(self.child(name))

    def link(self, source: str, destination: str) -> None:
        if self.directory_fd is not None:
            os.link(
                source,
                destination,
                src_dir_fd=self.directory_fd,
                dst_dir_fd=self.directory_fd,
                follow_symlinks=False,
            )
            return
        if self.windows_handles:
            _windows_rebind_name(
                self.windows_handles[-1], source, destination, replace=False, link=True
            )
            return
        os.link(self.child(source), self.child(destination), follow_symlinks=False)

    @contextmanager
    def bind_child_directory(
        self,
        name: str,
        *,
        create: bool = False,
        mode: int = 0o700,
    ) -> Iterator[BoundParent]:
        """Open one child directory relative to this held parent."""
        child = self.child(name)
        if self.directory_fd is not None:
            if create:
                os.mkdir(name, mode, dir_fd=self.directory_fd)
            flags = os.O_RDONLY | int(getattr(os, "O_DIRECTORY", 0)) | int(
                getattr(os, "O_NOFOLLOW", 0)
            )
            descriptor = os.open(name, flags, dir_fd=self.directory_fd)
            try:
                metadata = os.fstat(descriptor)
                if not stat.S_ISDIR(metadata.st_mode):
                    raise NotADirectoryError(child)
                yield BoundParent(child, directory_fd=descriptor)
            finally:
                os.close(descriptor)
            return
        if self.windows_handles:
            handle = _windows_nt_open(
                self.windows_handles[-1],
                name,
                desired_access=0x00000001 | 0x80,
                disposition=2 if create else 1,
                directory=True,
            )
            try:
                attributes, _volume, _index = _windows_handle_identity(handle)
                if attributes & _WINDOWS_REPARSE_POINT or not attributes & 0x10:
                    raise OSError("bound child is redirecting or not a directory")
                yield BoundParent(child, windows_handles=(handle,))
            finally:
                _windows_close_handle(handle)
            return
        if create:
            os.mkdir(child, mode)
        with bind_parent(child) as bound:
            yield bound
    def rename_noreplace(
        self,
        source: str,
        destination: str,
        *,
        expected_identity: tuple[int, int] | None = None,
    ) -> None:
        """Rename one held child directory without replacing another name."""
        self.child(source)
        self.child(destination)
        def require(actual: tuple[int, int]) -> None:
            if expected_identity is not None and actual != expected_identity:
                raise OSError("rename source identity changed")

        if self.directory_fd is not None:
            metadata = self.lstat(source)
            require((metadata.st_dev, metadata.st_ino))
            _posix_rename_noreplace(self.directory_fd, source, destination)
            return
        if self.windows_handles:
            for attempt in range(3):
                try:
                    _windows_rebind_name(
                        self.windows_handles[-1], source, destination,
                        replace=False, link=False, directory=True,
                        expected_identity=expected_identity,
                    )
                    return
                except PermissionError:
                    if attempt == 2:
                        raise
            return
        if os.path.lexists(self.child(destination)):
            raise FileExistsError(destination)
        metadata = os.lstat(self.child(source))
        require((metadata.st_dev, metadata.st_ino))
        os.rename(self.child(source), self.child(destination))

    def replace(self, source: str, destination: str) -> None:
        if self.directory_fd is not None:
            os.replace(
                source,
                destination,
                src_dir_fd=self.directory_fd,
                dst_dir_fd=self.directory_fd,
            )
            return
        if self.windows_handles:
            _windows_rebind_name(
                self.windows_handles[-1], source, destination, replace=True, link=False
            )
            return
        os.replace(self.child(source), self.child(destination))

    def unlink_if_identity(
        self,
        name: str,
        expected: tuple[int, int, int, int, int],
    ) -> bool:
        """Delete only the child object opened with ``expected`` identity."""

        if os.name == "nt":
            return _windows_unlink_opened(
                self.windows_handles[-1], name, self.child(name), expected
            )
        try:
            flags = os.O_RDONLY | int(getattr(os, "O_NOFOLLOW", 0))
            descriptor = self.open(name, flags)
            try:
                if _identity(os.fstat(descriptor)) != expected:
                    return False
                if _identity(self.lstat(name)) != expected:
                    return False
                os.unlink(name, dir_fd=self.directory_fd)
                return True
            finally:
                os.close(descriptor)
        except FileNotFoundError:
            return False



def _windows_open_directory(path: Path) -> int:
    import ctypes
    from ctypes import wintypes

    create_file = ctypes.windll.kernel32.CreateFileW
    create_file.argtypes = (
        wintypes.LPCWSTR,
        wintypes.DWORD,
        wintypes.DWORD,
        wintypes.LPVOID,
        wintypes.DWORD,
        wintypes.DWORD,
        wintypes.HANDLE,
    )
    create_file.restype = wintypes.HANDLE
    handle = create_file(
        os.fspath(path),
        0x80,
        0x1 | 0x2,
        None,
        3,
        0x02000000 | 0x00200000,
        None,
    )
    if handle == wintypes.HANDLE(-1).value:
        raise ctypes.WinError()
    return int(handle)


def _windows_handle_identity(handle: int) -> tuple[int, int, int]:
    import ctypes
    from ctypes import wintypes
    class FileInformation(ctypes.Structure):
        _fields_ = [
            ("attributes", wintypes.DWORD),
            ("creation_time", wintypes.FILETIME),
            ("access_time", wintypes.FILETIME),
            ("write_time", wintypes.FILETIME),
            ("volume_serial", wintypes.DWORD),
            ("size_high", wintypes.DWORD),
            ("size_low", wintypes.DWORD),
            ("links", wintypes.DWORD),
            ("index_high", wintypes.DWORD),
            ("index_low", wintypes.DWORD),
        ]
    information = FileInformation()
    function = ctypes.windll.kernel32.GetFileInformationByHandle
    function.argtypes = (wintypes.HANDLE, ctypes.POINTER(FileInformation))
    function.restype = wintypes.BOOL
    if not function(handle, ctypes.byref(information)):
        raise ctypes.WinError()
    index = (information.index_high << 32) | information.index_low
    return information.attributes, information.volume_serial, index


def _windows_nt_open(
    parent_handle: int,
    name: str,
    *,
    desired_access: int,
    disposition: int,
    share_access: int = 0x1 | 0x2 | 0x4,
    directory: bool = False,
) -> int:
    import ctypes
    from ctypes import wintypes
    class UnicodeString(ctypes.Structure):
        _fields_ = [
            ("length", wintypes.USHORT),
            ("maximum_length", wintypes.USHORT),
            ("buffer", wintypes.LPWSTR),
        ]
    class ObjectAttributes(ctypes.Structure):
        _fields_ = [
            ("length", wintypes.ULONG),
            ("root_directory", wintypes.HANDLE),
            ("object_name", ctypes.POINTER(UnicodeString)),
            ("attributes", wintypes.ULONG),
            ("security_descriptor", wintypes.LPVOID),
            ("security_qos", wintypes.LPVOID),
        ]
    class IoStatusBlock(ctypes.Structure):
        _fields_ = [("status", ctypes.c_void_p), ("information", ctypes.c_size_t)]
    encoded = name.encode("utf-16-le")
    buffer = ctypes.create_unicode_buffer(name)
    unicode_name = UnicodeString(
        len(encoded), len(encoded) + 2, ctypes.cast(buffer, wintypes.LPWSTR)
    )
    attributes = ObjectAttributes(
        ctypes.sizeof(ObjectAttributes),
        parent_handle,
        ctypes.pointer(unicode_name),
        0x40,
        None,
        None,
    )
    io_status = IoStatusBlock()
    handle = wintypes.HANDLE()
    function = ctypes.windll.ntdll.NtCreateFile
    function.argtypes = (
        ctypes.POINTER(wintypes.HANDLE),
        wintypes.ULONG,
        ctypes.POINTER(ObjectAttributes),
        ctypes.POINTER(IoStatusBlock),
        ctypes.c_void_p,
        wintypes.ULONG,
        wintypes.ULONG,
        wintypes.ULONG,
        wintypes.ULONG,
        ctypes.c_void_p,
        wintypes.ULONG,
    )
    function.restype = ctypes.c_long
    status = function(
        ctypes.byref(handle),
        desired_access | 0x00100000,
        ctypes.byref(attributes),
        ctypes.byref(io_status),
        None,
        0x80,
        share_access,
        disposition,
        0x20 | (0x1 if directory else 0x40) | 0x00200000,
        None,
        0,
    )
    if status < 0:
        unsigned = ctypes.c_ulong(status).value
        if unsigned == 0xC0000035:
            raise FileExistsError(name)
        if unsigned in {0xC0000034, 0xC000003A}:
            raise FileNotFoundError(name)
        converter = ctypes.windll.ntdll.RtlNtStatusToDosError
        converter.argtypes = (wintypes.ULONG,)
        converter.restype = wintypes.ULONG
        raise ctypes.WinError(converter(unsigned))
    return int(handle.value)


def _windows_open_relative(parent_handle: int, name: str, flags: int) -> int:
    import ctypes
    import msvcrt
    from ctypes import wintypes
    access = flags & (os.O_RDONLY | os.O_WRONLY | os.O_RDWR)
    desired = 0xC0000000 if access == os.O_RDWR else 0x40000000
    if access == os.O_RDONLY:
        desired = 0x80000000
    disposition = 2 if flags & os.O_CREAT and flags & os.O_EXCL else 1
    handle = _windows_nt_open(
        parent_handle, name, desired_access=desired, disposition=disposition
    )
    try:
        return msvcrt.open_osfhandle(handle, flags)
    except Exception:
        close_handle = ctypes.windll.kernel32.CloseHandle
        close_handle.argtypes = (wintypes.HANDLE,)
        close_handle(handle)
        raise


def _windows_rebind_name(
    parent_handle: int,
    source: str,
    destination: str,
    *,
    replace: bool,
    link: bool,
    directory: bool = False,
    expected_identity: tuple[int, int] | None = None,
) -> None:
    import ctypes
    from ctypes import wintypes
    handle = _windows_nt_open(
        parent_handle,
        source,
        desired_access=0x00010000 | 0x80,
        disposition=1,
        directory=directory,
    )
    if expected_identity is not None:
        _attributes, volume, index = _windows_handle_identity(handle)
        if (volume, index) != expected_identity:
            _windows_close_handle(handle)
            raise OSError("rename source identity changed")
    class NameInformation(ctypes.Structure):
        _fields_ = [
            ("replace", wintypes.BOOLEAN),
            ("root_directory", wintypes.HANDLE),
            ("name_length", wintypes.DWORD),
            ("name", wintypes.WCHAR * 1),
        ]
    encoded = destination.encode("utf-16-le")
    offset = NameInformation.name.offset
    storage = ctypes.create_string_buffer(ctypes.sizeof(NameInformation) + len(encoded))
    information = ctypes.cast(storage, ctypes.POINTER(NameInformation)).contents
    information.replace = bool(replace)
    information.root_directory = parent_handle
    information.name_length = len(encoded)
    ctypes.memmove(ctypes.addressof(storage) + offset, encoded, len(encoded))
    class IoStatusBlock(ctypes.Structure):
        _fields_ = [("status", ctypes.c_void_p), ("information", ctypes.c_size_t)]
    io_status = IoStatusBlock()
    function = ctypes.windll.ntdll.NtSetInformationFile
    function.argtypes = (
        wintypes.HANDLE,
        ctypes.POINTER(IoStatusBlock),
        wintypes.LPVOID,
        wintypes.ULONG,
        wintypes.ULONG,
    )
    function.restype = ctypes.c_long
    try:
        status = function(
            handle,
            ctypes.byref(io_status),
            storage,
            len(storage),
            11 if link else 10,
        )
        if status < 0:
            unsigned = ctypes.c_ulong(status).value
            if unsigned in {0xC0000035, 0xC000003A}:
                raise FileExistsError(destination)
            converter = ctypes.windll.ntdll.RtlNtStatusToDosError
            converter.argtypes = (wintypes.ULONG,)
            converter.restype = wintypes.ULONG
            raise ctypes.WinError(converter(unsigned))
    finally:
        close_handle = ctypes.windll.kernel32.CloseHandle
        close_handle.argtypes = (wintypes.HANDLE,)
        close_handle(handle)


def _windows_close_handle(handle: int) -> None:
    import ctypes
    from ctypes import wintypes
    close_handle = ctypes.windll.kernel32.CloseHandle
    close_handle.argtypes = (wintypes.HANDLE,)
    close_handle.restype = wintypes.BOOL
    close_handle(handle)


def _posix_rename_noreplace(directory_fd: int, source: str, destination: str) -> None:
    import ctypes
    libc = ctypes.CDLL(None, use_errno=True)
    renameat2 = getattr(libc, "renameat2", None)
    if renameat2 is None:
        raise OSError("safe no-replace directory rename is unavailable")
    renameat2.argtypes = (ctypes.c_int, ctypes.c_char_p) * 2 + (ctypes.c_uint,)
    renameat2.restype = ctypes.c_int
    result = renameat2(directory_fd, os.fsencode(source), directory_fd, os.fsencode(destination), 1)
    if result != 0:
        code = ctypes.get_errno()
        if code == 17:
            raise FileExistsError(destination)
        raise OSError(code, os.strerror(code))


def _windows_unlink_opened(
    parent_handle: int,
    name: str,
    display_path: Path,
    expected: tuple[int, int, int, int, int],
) -> bool:
    import ctypes
    import msvcrt
    from ctypes import wintypes
    try:
        handle = _windows_nt_open(
            parent_handle,
            name,
            desired_access=0x00010000 | 0x80,
            disposition=1,
            share_access=0x1 | 0x2,
        )
    except FileNotFoundError:
        return False
    descriptor = msvcrt.open_osfhandle(int(handle), os.O_RDONLY)
    try:
        if _identity(os.fstat(descriptor)) != expected:
            return False
        _before_owned_handle_delete(display_path)
        class FileDisposition(ctypes.Structure):
            _fields_ = [("delete_file", wintypes.BOOLEAN)]
        disposition = FileDisposition(True)
        class IoStatusBlock(ctypes.Structure):
            _fields_ = [("status", ctypes.c_void_p), ("information", ctypes.c_size_t)]
        io_status = IoStatusBlock()
        function = ctypes.windll.ntdll.NtSetInformationFile
        function.argtypes = (
            wintypes.HANDLE,
            ctypes.POINTER(IoStatusBlock),
            wintypes.LPVOID,
            wintypes.ULONG,
            wintypes.ULONG,
        )
        function.restype = ctypes.c_long
        status = function(
            handle,
            ctypes.byref(io_status),
            ctypes.byref(disposition),
            ctypes.sizeof(disposition),
            13,
        )
        if status < 0:
            converter = ctypes.windll.ntdll.RtlNtStatusToDosError
            converter.argtypes = (wintypes.ULONG,)
            converter.restype = wintypes.ULONG
            raise ctypes.WinError(converter(ctypes.c_ulong(status).value))
        return True
    finally:
        os.close(descriptor)


@contextmanager
def bind_parent(parent: Path) -> Iterator[BoundParent]:
    """Hold a stable no-follow binding for an existing absolute directory."""
    candidate = Path(os.path.abspath(parent))
    expected = os.lstat(candidate)
    if not stat.S_ISDIR(expected.st_mode):
        raise NotADirectoryError(candidate)
    if os.name != "nt":
        flags = os.O_RDONLY | int(getattr(os, "O_DIRECTORY", 0))
        flags |= int(getattr(os, "O_NOFOLLOW", 0))
        descriptor = os.open(candidate, flags)
        try:
            if _identity(os.fstat(descriptor))[:3] != _identity(expected)[:3]:
                raise OSError("parent directory changed while it was being bound")
            yield BoundParent(candidate, directory_fd=descriptor)
        finally:
            os.close(descriptor)
        return

    handles: list[int] = []
    try:
        for component in reversed((candidate, *candidate.parents)):
            metadata = os.lstat(component)
            handle = _windows_open_directory(component)
            handles.append(handle)
            attributes, _volume, index = _windows_handle_identity(handle)
            if attributes & _WINDOWS_REPARSE_POINT or not attributes & 0x10:
                raise OSError("bound ancestry contains a reparse point or non-directory")
            if metadata.st_ino and index != metadata.st_ino:
                raise OSError("directory ancestry changed while it was being bound")
        yield BoundParent(candidate, windows_handles=tuple(handles))
    finally:
        if handles:
            import ctypes
            from ctypes import wintypes

            close_handle = ctypes.windll.kernel32.CloseHandle
            close_handle.argtypes = (wintypes.HANDLE,)
            close_handle.restype = wintypes.BOOL
            for handle in reversed(handles):
                close_handle(handle)


__all__ = ("BoundParent", "bind_parent")
