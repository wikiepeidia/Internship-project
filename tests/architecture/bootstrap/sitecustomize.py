"""Fail-closed Phase 41.1 authority guard installed by Python startup.

Policy is derived from literal strings only. The module never probes a protected
root, and guarded Python receives no process-launch exception.
"""

from __future__ import annotations

import builtins
import ctypes
import _ctypes
import glob as glob_module
import io
import ntpath
import os
from pathlib import Path
import subprocess
import sys
from types import MappingProxyType
from typing import Any, Callable

try:  # pytest imports colorama after startup; preload its fixed console functions.
    import colorama as _phase411_colorama  # noqa: F401
except ImportError:  # pragma: no cover - optional pytest dependency
    _phase411_colorama = None


PHASE411_GUARD_POLICY_VERSION = "phase411-guard-v3"
PHASE411_PROCESS_POLICY = "audited-python-native-load-deny"
PHASE411_GUARD_BOUNDARY = "audited-interpreter-native-load-denied"
PHASE411_PREINSTALL_DESCRIPTOR_PROBES = 0
PHASE411_GUARD_INSTALLED = False
PHASE411_AUDIT_GUARD_INSTALLED = False

_REJECTED: list[dict[str, str]] = []
_AUDIT_REJECTED: list[dict[str, str]] = []
_UNDERLYING_FORBIDDEN: list[dict[str, str]] = []
_DESCRIPTOR_REMOVALS: list[int] = []
_DESCRIPTOR_CAPABILITIES: set[int] = set()

_BOOTSTRAP_DIR = ntpath.abspath(ntpath.dirname(__file__))
_REPO_ROOT = ntpath.abspath(ntpath.join(_BOOTSTRAP_DIR, "..", "..", ".."))
_PROTECTED_ROOT_SPECS = (
    "repo:data/splits",
    r"C:\ProgramData\VNPhish\phase41-evaluation-evidence",
    "repo:historical/phase41-source-closure",
    "repo:data/models/phase41",
    r"D:\PROJEct\AI MODELS\phase40-full-local-20260825",
    r"D:\PROJEct\AI MODELS\base\qwen2.5-7b-instruct",
    r"D:\PROJEct\AI MODELS\base\qwen3.5-4b",
)


def _root_from_spec(spec: str) -> str:
    if spec.startswith("repo:"):
        relative = spec.removeprefix("repo:").replace("/", "\\")
        value = ntpath.join(_REPO_ROOT, relative)
    else:
        value = spec
    return ntpath.normcase(ntpath.normpath(value))


PHASE411_PROTECTED_ROOTS = tuple(_root_from_spec(spec) for spec in _PROTECTED_ROOT_SPECS)
PHASE411_PROTECTED_PREFIX = PHASE411_PROTECTED_ROOTS[0]

_PROCESS_OPERATION_NAMES = (
    "os.system", "os.popen", "os.startfile", "os.spawnl", "os.spawnle",
    "os.spawnv", "os.spawnve", "os.execl", "os.execle", "os.execlp",
    "os.execlpe", "os.execv", "os.execve", "os.execvp", "os.execvpe",
    "os.spawnlp", "os.spawnlpe", "os.spawnvp", "os.spawnvpe", "os.fork",
    "os.forkpty", "os.posix_spawn", "os.posix_spawnp",
    "subprocess.Popen.__init__", "subprocess.run", "subprocess.call",
    "subprocess.check_call", "subprocess.check_output", "subprocess.getoutput",
    "subprocess.getstatusoutput", "asyncio.create_subprocess_exec",
    "asyncio.create_subprocess_shell", "asyncio.BaseEventLoop.subprocess_exec",
    "asyncio.BaseEventLoop.subprocess_shell", "multiprocessing.Process",
    "multiprocessing.Pool", "multiprocessing.process.BaseProcess.start",
    "multiprocessing.context.BaseContext.Pool",
    "multiprocessing.context.DefaultContext.Process",
    "multiprocessing.context.DefaultContext.Pool",
    "multiprocessing.context.SpawnContext.Process",
    "multiprocessing.context.SpawnContext.Pool",
    "multiprocessing.pool.Pool.__init__",
    "multiprocessing.popen_spawn_win32.Popen.__init__",
    "multiprocessing.managers.BaseManager.start",
    "multiprocessing.resource_tracker.ResourceTracker.ensure_running",
    "multiprocessing.forkserver.ForkServer.ensure_running",
    "multiprocessing.util.spawnv_passfds",
    "concurrent.futures.ProcessPoolExecutor.__init__", "_winapi.CreateProcess",
    "_posixsubprocess.fork_exec", "subprocess._fork_exec", "pty.spawn",
)

_NATIVE_PROCESS_OPERATION_NAMES = (
    "nt.system",
    "posix.system",
    "ctypes.CDLL.__init__",
    "ctypes.PyDLL.__init__",
    "ctypes.WinDLL.__init__",
    "ctypes.OleDLL.__init__",
    "ctypes.LibraryLoader.__getattr__",
    "ctypes._dlopen",
    "_ctypes.dlopen",
    "importlib.reload",
)
_AUDITED_PROCESS_EVENTS = frozenset(
    {"ctypes.dlopen", "os.system", "os.posix_spawn", "subprocess.Popen"}
)


def _strip_windows_namespace(value: str) -> str:
    normalized = value.replace("/", "\\")
    lowered = normalized.casefold()
    if lowered.startswith("\\\\?\\unc\\"):
        return "\\\\" + normalized[8:]
    for prefix in ("\\\\?\\", "\\??\\", "\\\\.\\"):
        if lowered.startswith(prefix.casefold()):
            return normalized[len(prefix):]
    return normalized


def _lexical_path(value: object) -> str | None:
    if isinstance(value, int):
        return None
    try:
        raw = os.fsdecode(os.fspath(value))
    except TypeError:
        return None
    raw = _strip_windows_namespace(raw)
    drive, tail = ntpath.splitdrive(raw)
    if drive and tail and not tail.startswith(("\\", "/")):
        raise PermissionError("Phase 41.1 drive-relative path spelling is forbidden")
    return ntpath.normcase(ntpath.normpath(ntpath.abspath(raw)))


def _is_forbidden(value: object) -> tuple[bool, str | None]:
    normalized = _lexical_path(value)
    if normalized is None:
        return False, None
    for root in PHASE411_PROTECTED_ROOTS:
        if normalized == root or normalized.startswith(root + "\\") or normalized.startswith(root + ":"):
            return True, normalized
    return False, normalized


def _reject_path(operation: str, value: object) -> None:
    forbidden, normalized = _is_forbidden(value)
    if not forbidden:
        return
    _REJECTED.append({"operation": operation, "path": normalized or ""})
    raise PermissionError(
        f"Phase 41.1 forbidden authority path blocked before filesystem call: {operation}"
    )


_AUDITED_PATH_ARGUMENTS = MappingProxyType(
    {
        "open": (0,),
        "os.chdir": (0,),
        "os.chmod": (0,),
        "os.chown": (0,),
        "os.listdir": (0,),
        "os.scandir": (0,),
        "os.mkdir": (0,),
        "os.remove": (0,),
        "os.rmdir": (0,),
        "os.truncate": (0,),
        "os.utime": (0,),
        "os.rename": (0, 1),
        "os.link": (0, 1),
        "os.symlink": (0, 1),
        "glob.glob": (0,),
        "glob.glob/2": (0,),
    }
)


def _phase411_audit_hook(event: str, args: tuple[object, ...]) -> None:
    """Deny protected paths below wrappers through CPython's append-only hook."""

    if event in _AUDITED_PROCESS_EVENTS:
        _AUDIT_REJECTED.append({"operation": event, "path": "<process-denied>"})
        _REJECTED.append({"operation": f"audit:{event}", "path": "<process-denied>"})
        raise PermissionError(f"Phase 41.1 audited process execution denied: {event}")
    for position in _AUDITED_PATH_ARGUMENTS.get(event, ()):
        if position >= len(args):
            continue
        forbidden, normalized = _is_forbidden(args[position])
        if not forbidden:
            continue
        _AUDIT_REJECTED.append({"operation": event, "path": normalized or ""})
        _REJECTED.append({"operation": f"audit:{event}", "path": normalized or ""})
        raise PermissionError(
            f"Phase 41.1 audited authority path blocked before filesystem call: {event}"
        )


def _make_path_guard(
    name: str,
    original: Callable[..., Any],
    path_positions: tuple[int, ...] = (0,),
    path_keywords: tuple[str, ...] = (),
) -> Callable[..., Any]:
    def guard(*args: Any, **kwargs: Any) -> Any:
        values = [args[position] for position in path_positions if position < len(args)]
        values.extend(kwargs[key] for key in path_keywords if key in kwargs)
        if any(key.endswith("dir_fd") and value is not None for key, value in kwargs.items()):
            _REJECTED.append({"operation": name, "path": "<descriptor-relative>"})
            raise PermissionError(
                f"Phase 41.1 descriptor-relative filesystem call blocked: {name}"
            )
        for value in values:
            _reject_path(name, value)
        return original(*args, **kwargs)

    setattr(guard, "__phase411_path_guard__", name)
    return guard


def _patch_path(
    target: object,
    attribute: str,
    *,
    positions: tuple[int, ...] = (0,),
    keywords: tuple[str, ...] = (),
) -> str | None:
    name = f"{getattr(target, '__name__', type(target).__name__)}.{attribute}"
    original = getattr(target, attribute, None)
    if original is None:
        return None
    setattr(target, attribute, _make_path_guard(name, original, positions, keywords))
    return name


def _make_process_deny_wrapper(name: str) -> Callable[..., Any]:
    def deny(*_args: Any, **_kwargs: Any) -> Any:
        _REJECTED.append({"operation": name, "path": "<process-denied>"})
        raise PermissionError(f"Phase 41.1 process execution denied: {name}")

    setattr(deny, "__phase411_process_guard__", name)
    return deny


def _resolve_process_owner(name: str) -> tuple[object, str] | None:
    parts = name.split(".")
    module = sys.modules.get(parts[0])
    if module is None:
        try:
            module = __import__(parts[0])
        except (ImportError, OSError):
            return None
    owner: object = module
    for index, part in enumerate(parts[1:-1], start=1):
        child = getattr(owner, part, None)
        if child is None:
            try:
                child = __import__(".".join(parts[:index + 1]), fromlist=[part])
            except (ImportError, OSError):
                return None
        owner = child
    attribute = parts[-1]
    if not hasattr(owner, attribute):
        return None
    return owner, attribute


def _patch_process(name: str) -> bool:
    resolved = _resolve_process_owner(name)
    if resolved is None:
        return False
    owner, attribute = resolved
    original = getattr(owner, attribute)
    if not callable(original):
        return False
    setattr(owner, attribute, _make_process_deny_wrapper(name))
    return True


def _deny_descriptor(name: str, descriptor: object) -> int:
    if not isinstance(descriptor, int) or descriptor not in _DESCRIPTOR_CAPABILITIES:
        _REJECTED.append({"operation": name, "path": "<unknown-descriptor>"})
        raise PermissionError(f"Phase 41.1 descriptor capability denied: {name}")
    return descriptor


def _make_descriptor_consumer(
    name: str,
    original: Callable[..., Any],
    positions: tuple[int, ...] = (0,),
    keywords: tuple[str, ...] = ("fd",),
) -> Callable[..., Any]:
    def guard(*args: Any, **kwargs: Any) -> Any:
        for position in positions:
            if position < len(args):
                _deny_descriptor(name, args[position])
        for keyword in keywords:
            if keyword in kwargs:
                _deny_descriptor(name, kwargs[keyword])
        return original(*args, **kwargs)

    setattr(guard, "__phase411_descriptor_guard__", name)
    return guard


def _register_descriptor(value: object) -> None:
    if isinstance(value, int) and value >= 0:
        _DESCRIPTOR_CAPABILITIES.add(value)


def phase411_register_bound_descriptor(value: object) -> None:
    """Register one test-fixture descriptor only after the startup guard exists."""

    if not PHASE411_GUARD_INSTALLED:
        raise RuntimeError("descriptor registration requires an installed startup guard")
    _register_descriptor(value)


def _install_path_guards() -> tuple[str, ...]:
    installed: list[str] = []
    for target, attribute, positions, keywords in (
        (builtins, "open", (0,), ("file",)), (io, "open", (0,), ("file",)),
        (glob_module, "glob", (0,), ("pathname",)),
        (glob_module, "iglob", (0,), ("pathname",)),
    ):
        result = _patch_path(target, attribute, positions=positions, keywords=keywords)
        if result:
            installed.append(result)
    os_path_keywords = {
        "access": ("path",), "open": ("path",), "stat": ("path",),
        "lstat": ("path",), "listdir": ("path",), "scandir": ("path",),
        "walk": ("top",), "chdir": ("path",), "mkdir": ("path",),
        "makedirs": ("name",), "remove": ("path",), "unlink": ("path",),
        "rmdir": ("path",), "readlink": ("path",), "chmod": ("path",),
        "lchmod": ("path",), "chown": ("path",), "lchown": ("path",),
        "truncate": ("path",), "utime": ("path",), "statvfs": ("path",),
        "pathconf": ("path",), "mkfifo": ("path",), "mknod": ("path",),
    }
    for attribute, keywords in os_path_keywords.items():
        result = _patch_path(os, attribute, keywords=keywords)
        if result:
            installed.append(result)
    for attribute in ("rename", "replace", "link", "symlink"):
        result = _patch_path(os, attribute, positions=(0, 1), keywords=("src", "dst"))
        if result:
            installed.append(result)
    for attribute in (
        "open", "read_bytes", "read_text", "write_bytes", "write_text", "stat",
        "lstat", "exists", "is_file", "is_dir", "is_symlink", "iterdir", "glob",
        "rglob", "resolve", "absolute", "touch", "mkdir", "unlink", "rmdir",
        "readlink", "chmod", "lchmod", "symlink_to", "hardlink_to",
    ):
        result = _patch_path(Path, attribute)
        if result:
            installed.append(result)
    for attribute in ("rename", "replace"):
        result = _patch_path(Path, attribute, positions=(0, 1), keywords=("target",))
        if result:
            installed.append(result)
    return tuple(installed)


def _install_low_level_process_denial() -> dict[str, str]:
    dispositions: dict[str, str] = {}
    low_level = set(_PROCESS_OPERATION_NAMES[:24]) | {
        "_winapi.CreateProcess", "_posixsubprocess.fork_exec", "subprocess._fork_exec"
    }
    for name in _PROCESS_OPERATION_NAMES:
        if name in low_level:
            dispositions[name] = "wrapped" if _patch_process(name) else "unavailable_on_platform"
    return dispositions


def _install_native_process_denial() -> dict[str, str]:
    dispositions: dict[str, str] = {}
    for name in _NATIVE_PROCESS_OPERATION_NAMES:
        dispositions[name] = (
            "wrapped" if _patch_process(name) else "unavailable_on_platform"
        )
    return dispositions


def _clear_ctypes_loader_cache() -> None:
    """Drop DLL objects cached while trusted pytest console support imported."""

    for loader_name in ("cdll", "pydll", "windll", "oledll"):
        loader = getattr(ctypes, loader_name, None)
        if loader is None:
            continue
        for attribute in tuple(vars(loader)):
            if not attribute.startswith("_"):
                delattr(loader, attribute)


def _attest_standard_handles_after_guards() -> None:
    if os.name != "nt":
        return
    try:
        import _winapi
        import msvcrt
    except ImportError:
        return
    accepted = {_winapi.FILE_TYPE_CHAR, _winapi.FILE_TYPE_PIPE}
    for descriptor in (0, 1, 2):
        try:
            handle = msvcrt.get_osfhandle(descriptor)
            file_type = _winapi.GetFileType(handle)
        except (OSError, ValueError):
            continue
        if file_type in accepted:
            _register_descriptor(descriptor)


def _install_descriptor_guards() -> tuple[str, ...]:
    installed: list[str] = []

    def wrap_open(target: object, attribute: str) -> None:
        original = getattr(target, attribute)
        name = f"{getattr(target, '__name__', type(target).__name__)}.{attribute}"

        def guarded(file: object, *args: Any, **kwargs: Any) -> Any:
            if isinstance(file, int):
                _deny_descriptor(name, file)
            result = original(file, *args, **kwargs)
            try:
                _register_descriptor(result.fileno())
            except (AttributeError, OSError, ValueError):
                pass
            return result

        setattr(guarded, "__phase411_path_guard__", name)
        setattr(target, attribute, guarded)
        installed.append(name)

    wrap_open(builtins, "open")
    wrap_open(io, "open")

    original_os_open = os.open

    def guarded_os_open(*args: Any, **kwargs: Any) -> int:
        descriptor = original_os_open(*args, **kwargs)
        _register_descriptor(descriptor)
        return descriptor

    setattr(guarded_os_open, "__phase411_path_guard__", "os.open")
    os.open = guarded_os_open
    installed.append("os.open")

    if hasattr(os, "pipe"):
        original_pipe = os.pipe

        def guarded_pipe(*args: Any, **kwargs: Any) -> tuple[int, int]:
            pair = original_pipe(*args, **kwargs)
            _register_descriptor(pair[0])
            _register_descriptor(pair[1])
            return pair

        os.pipe = guarded_pipe
        installed.append("os.pipe")

    for attribute in (
        "fdopen", "fstat", "fchmod", "ftruncate", "fsync", "read", "write",
        "lseek", "fchdir", "pread", "readv", "preadv",
    ):
        original = getattr(os, attribute, None)
        if original is None:
            continue
        name = f"os.{attribute}"
        setattr(
            os,
            attribute,
            _make_descriptor_consumer(name, original, keywords=("fd",)),
        )
        installed.append(name)

    def make_duplicate_guard(
        name: str,
        original: Callable[..., Any],
        *,
        target_keyword: str | None,
    ) -> Callable[..., Any]:
        def duplicate(*args: Any, **kwargs: Any) -> Any:
            source = args[0] if args else kwargs.get("fd")
            _deny_descriptor(name, source)
            target = None
            if target_keyword is not None:
                target = args[1] if len(args) > 1 else kwargs.get(target_keyword)
                _deny_descriptor(name, target)
            result = original(*args, **kwargs)
            _register_descriptor(result if isinstance(result, int) else target)
            return result

        setattr(duplicate, "__phase411_descriptor_guard__", name)
        return duplicate

    for attribute, target_keyword in (("dup", None), ("dup2", "fd2")):
        original = getattr(os, attribute, None)
        if original is None:
            continue
        name = f"os.{attribute}"
        setattr(
            os,
            attribute,
            make_duplicate_guard(name, original, target_keyword=target_keyword),
        )
        installed.append(name)

    if hasattr(os, "close"):
        original_close = os.close

        def guarded_close(fd: object) -> None:
            descriptor = _deny_descriptor("os.close", fd)
            try:
                return original_close(descriptor)
            finally:
                _DESCRIPTOR_CAPABILITIES.discard(descriptor)
                _DESCRIPTOR_REMOVALS.append(descriptor)

        os.close = guarded_close
        installed.append("os.close")
    return tuple(installed)


def phase411_guard_snapshot() -> dict[str, object]:
    return {
        "rejected": [dict(item) for item in _REJECTED],
        "audit_rejected": [dict(item) for item in _AUDIT_REJECTED],
        "underlying_forbidden": [dict(item) for item in _UNDERLYING_FORBIDDEN],
        "descriptor_removals": tuple(_DESCRIPTOR_REMOVALS),
    }


def phase411_descriptor_capabilities() -> tuple[int, ...]:
    return tuple(sorted(_DESCRIPTOR_CAPABILITIES))


def install_phase411_deny_open_guard() -> None:
    global PHASE411_AUDIT_GUARD_INSTALLED
    global PHASE411_GUARD_INSTALLED
    global PHASE411_INSTALLED_PATH_OPERATIONS
    global PHASE411_INSTALLED_DESCRIPTOR_OPERATIONS
    global PHASE411_INSTALLED_PROCESS_OPERATIONS
    global PHASE411_PROCESS_OPERATION_DISPOSITIONS
    global PHASE411_NATIVE_PROCESS_OPERATION_DISPOSITIONS
    if PHASE411_GUARD_INSTALLED:
        return
    sys.addaudithook(_phase411_audit_hook)
    PHASE411_AUDIT_GUARD_INSTALLED = True
    PHASE411_INSTALLED_PATH_OPERATIONS = _install_path_guards()
    native_dispositions = _install_native_process_denial()
    _clear_ctypes_loader_cache()
    dispositions = _install_low_level_process_denial()
    _attest_standard_handles_after_guards()
    PHASE411_INSTALLED_DESCRIPTOR_OPERATIONS = _install_descriptor_guards()
    for name in _PROCESS_OPERATION_NAMES:
        if name not in dispositions:
            dispositions[name] = "wrapped" if _patch_process(name) else "unavailable_on_platform"
    PHASE411_PROCESS_OPERATION_DISPOSITIONS = MappingProxyType(
        {name: dispositions[name] for name in _PROCESS_OPERATION_NAMES}
    )
    PHASE411_NATIVE_PROCESS_OPERATION_DISPOSITIONS = MappingProxyType(
        {name: native_dispositions[name] for name in _NATIVE_PROCESS_OPERATION_NAMES}
    )
    PHASE411_INSTALLED_PROCESS_OPERATIONS = tuple(
        name for name in _PROCESS_OPERATION_NAMES if dispositions[name] == "wrapped"
    )
    PHASE411_GUARD_INSTALLED = True


PHASE411_INSTALLED_PATH_OPERATIONS: tuple[str, ...] = ()
PHASE411_INSTALLED_DESCRIPTOR_OPERATIONS: tuple[str, ...] = ()
PHASE411_INSTALLED_PROCESS_OPERATIONS: tuple[str, ...] = ()
PHASE411_PROCESS_OPERATION_DISPOSITIONS = MappingProxyType({})
PHASE411_NATIVE_PROCESS_OPERATION_DISPOSITIONS = MappingProxyType({})

if os.environ.get("PHASE411_DENY_OPEN_SENTINEL") == "1":
    install_phase411_deny_open_guard()
