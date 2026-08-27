"""Install the Phase 41.1 held-out-data deny-open guard at interpreter startup."""

from __future__ import annotations

import builtins
import functools
import io
import ntpath
import os
from pathlib import Path
import re
import subprocess
import sys
from typing import Any, Callable


PHASE411_GUARD_INSTALLED = False
_REJECTED: list[dict[str, str]] = []
_UNDERLYING_FORBIDDEN: list[dict[str, str]] = []
_ORIGINALS: dict[str, Callable[..., Any]] = {}


def _startup_descriptors() -> frozenset[int]:
    inherited: set[int] = set()
    for descriptor in range(256):
        try:
            os.fstat(descriptor)
        except OSError:
            continue
        inherited.add(descriptor)
    return frozenset(inherited)


_INHERITED_FDS = _startup_descriptors()


def _strip_windows_namespace(value: str) -> str:
    normalized = value.replace("/", "\\")
    lowered = normalized.lower()
    if lowered.startswith("\\\\?\\unc\\"):
        return "\\\\" + normalized[8:]
    for prefix in ("\\\\?\\", "\\??\\", "\\\\.\\"):
        if lowered.startswith(prefix.lower()):
            return normalized[len(prefix) :]
    return normalized


def _lexical_path(value: object) -> str | None:
    if isinstance(value, int):
        return None
    try:
        raw = os.fsdecode(os.fspath(value))
    except TypeError:
        return None
    raw = _strip_windows_namespace(raw)
    return ntpath.normcase(ntpath.abspath(ntpath.normpath(raw)))


_BOOTSTRAP_DIR = ntpath.dirname(ntpath.abspath(__file__))
_REPO_ROOT = ntpath.abspath(ntpath.join(_BOOTSTRAP_DIR, "..", "..", ".."))
PHASE411_PROTECTED_PREFIX = ntpath.normpath(
    ntpath.join(_REPO_ROOT, "data", "splits")
)
_PROTECTED_NORMALIZED = ntpath.normcase(PHASE411_PROTECTED_PREFIX)


def _is_forbidden(value: object) -> tuple[bool, str | None]:
    normalized = _lexical_path(value)
    if normalized is None:
        return False, None
    forbidden = normalized == _PROTECTED_NORMALIZED or normalized.startswith(
        _PROTECTED_NORMALIZED + "\\"
    )
    return forbidden, normalized


def _reject(operation: str, value: object) -> None:
    forbidden, normalized = _is_forbidden(value)
    if not forbidden:
        return
    event = {"operation": operation, "path": normalized or ""}
    _REJECTED.append(event)
    raise PermissionError(
        f"Phase 41.1 forbidden path blocked before filesystem call: {operation}"
    )


def _wrapped(
    name: str,
    original: Callable[..., Any],
    path_positions: tuple[int, ...] = (0,),
    path_keywords: tuple[str, ...] = (),
) -> Callable[..., Any]:
    @functools.wraps(original)
    def guard(*args: Any, **kwargs: Any) -> Any:
        values: list[object] = []
        for position in path_positions:
            if position < len(args):
                values.append(args[position])
        values.extend(kwargs[key] for key in path_keywords if key in kwargs)
        if any(
            key.endswith("dir_fd") and value is not None
            for key, value in kwargs.items()
        ):
            raise PermissionError(
                f"Phase 41.1 descriptor-relative filesystem call blocked: {name}"
            )
        if any(
            isinstance(value, int) and value in _INHERITED_FDS for value in values
        ):
            raise PermissionError(
                f"Phase 41.1 inherited file descriptor blocked: {name}"
            )
        for value in values:
            _reject(name, value)
        for value in values:
            forbidden, normalized = _is_forbidden(value)
            if forbidden:  # Defensive proof hook; _reject must have raised first.
                _UNDERLYING_FORBIDDEN.append(
                    {"operation": name, "path": normalized or ""}
                )
        return original(*args, **kwargs)

    return guard


def _patch(
    target: object,
    attribute: str,
    *,
    positions: tuple[int, ...] = (0,),
    keywords: tuple[str, ...] = (),
) -> None:
    key = f"{getattr(target, '__name__', type(target).__name__)}.{attribute}"
    original = getattr(target, attribute, None)
    if original is None or key in _ORIGINALS:
        return
    _ORIGINALS[key] = original
    setattr(target, attribute, _wrapped(key, original, positions, keywords))


def _preserve_child_bootstrap() -> None:
    current = os.environ.get("PYTHONPATH", "")
    entries = [item for item in current.split(os.pathsep) if item]
    normalized = {ntpath.normcase(ntpath.abspath(item)) for item in entries}
    if ntpath.normcase(_BOOTSTRAP_DIR) not in normalized:
        os.environ["PYTHONPATH"] = os.pathsep.join([_BOOTSTRAP_DIR, *entries])


def _guarded_popen_init(original: Callable[..., Any]) -> Callable[..., Any]:
    """Permit only guarded child Python and reviewed read-only git commands."""

    @functools.wraps(original)
    def guard(self: object, args: object, *popen_args: object, **kwargs: object) -> Any:
        if kwargs.get("shell"):
            raise PermissionError("Phase 41.1 subprocess shell execution is forbidden")
        if kwargs.get("close_fds") is False or kwargs.get("pass_fds"):
            raise PermissionError("Phase 41.1 subprocess descriptor inheritance is forbidden")
        if not isinstance(args, (list, tuple)) or not args:
            raise PermissionError("Phase 41.1 subprocess arguments must be a closed sequence")
        if kwargs.get("executable") is not None:
            raise PermissionError("Phase 41.1 subprocess executable override is forbidden")
        argv = [os.fsdecode(os.fspath(value)) for value in args]
        for value in argv:
            _reject("subprocess.Popen", value)
        executable = ntpath.normcase(ntpath.abspath(_strip_windows_namespace(argv[0])))
        python = ntpath.normcase(ntpath.abspath(sys.executable))
        if executable == python:
            if any(flag in {"-S", "-I", "-E"} for flag in argv[1:]):
                raise PermissionError(
                    "Phase 41.1 child Python may not disable site or environment processing"
                )
            reviewed_python = (
                (len(argv) >= 3 and argv[1] == "-c")
                or (len(argv) >= 4 and argv[1:3] == ["-m", "pytest"])
                or (
                    len(argv) >= 2
                    and argv[1].casefold().endswith(".py")
                    and not argv[1].startswith("-")
                )
            )
            if not reviewed_python:
                raise PermissionError("Phase 41.1 child Python command grammar is not reviewed")
            environment = os.environ if kwargs.get("env") is None else kwargs["env"]
            if not hasattr(environment, "get"):
                raise PermissionError("Phase 41.1 child Python environment must be a mapping")
            if environment.get("PHASE411_DENY_OPEN_SENTINEL") != "1":
                raise PermissionError("Phase 41.1 child Python must inherit the deny-open sentinel")
            python_path = environment.get("PYTHONPATH", "")
            entries = {
                ntpath.normcase(ntpath.abspath(item))
                for item in python_path.split(os.pathsep)
                if item
            }
            if ntpath.normcase(_BOOTSTRAP_DIR) not in entries:
                raise PermissionError("Phase 41.1 child Python must inherit the deny-open bootstrap")
        elif ntpath.basename(executable) in {"git", "git.exe"}:
            relative = (
                r"(?!-)(?![A-Za-z]:[\\/])(?![\\/])"
                r"(?!.*(?:^|[\\/])\.\.(?:[\\/]|$))[^\x00]+"
            )
            safe_git = (
                argv[1:] == ["rev-parse", "HEAD"]
                or (
                    len(argv) == 3
                    and argv[1] == "rev-parse"
                    and re.fullmatch(rf"[0-9a-f]{{40}}:{relative}", argv[2]) is not None
                )
                or (
                    len(argv) == 4
                    and argv[1:3] == ["cat-file", "blob"]
                    and re.fullmatch(r"[0-9a-f]{40,64}", argv[3]) is not None
                )
                or (
                    len(argv) == 5
                    and argv[1:4] == ["ls-files", "--stage", "--"]
                    and re.fullmatch(relative, argv[4]) is not None
                )
            )
            if not safe_git:
                raise PermissionError("Phase 41.1 git subprocess is not in the read-only allowlist")
        else:
            raise PermissionError("Phase 41.1 non-Python subprocess is forbidden")
        return original(self, args, *popen_args, **kwargs)

    return guard


def phase411_guard_snapshot() -> dict[str, list[dict[str, str]]]:
    """Return recorder state without probing the protected filesystem prefix."""

    return {
        "rejected": [dict(item) for item in _REJECTED],
        "underlying_forbidden": [dict(item) for item in _UNDERLYING_FORBIDDEN],
    }


def install_phase411_deny_open_guard() -> None:
    """Patch path-taking primitives once, before pytest imports or collection."""

    global PHASE411_GUARD_INSTALLED
    if PHASE411_GUARD_INSTALLED:
        return
    _preserve_child_bootstrap()
    _patch(builtins, "open", keywords=("file",))
    _patch(io, "open", keywords=("file",))
    os_path_keywords = {
        "access": ("path",),
        "open": ("path",),
        "stat": ("path",),
        "lstat": ("path",),
        "listdir": ("path",),
        "scandir": ("path",),
        "walk": ("top",),
        "chdir": ("path",),
        "mkdir": ("path",),
        "makedirs": ("name",),
        "remove": ("path",),
        "unlink": ("path",),
        "rmdir": ("path",),
        "readlink": ("path",),
        "chmod": ("path",),
        "lchmod": ("path",),
        "chown": ("path",),
        "lchown": ("path",),
        "truncate": ("path",),
        "utime": ("path",),
        "statvfs": ("path",),
        "pathconf": ("path",),
        "mkfifo": ("path",),
        "mknod": ("path",),
    }
    for name, keywords in os_path_keywords.items():
        _patch(os, name, keywords=keywords)
    for name in ("rename", "replace"):
        _patch(os, name, positions=(0, 1), keywords=("src", "dst"))
    for name in ("link", "symlink"):
        _patch(os, name, positions=(0, 1), keywords=("src", "dst"))
    for name in (
        "open",
        "read_bytes",
        "read_text",
        "write_bytes",
        "write_text",
        "stat",
        "lstat",
        "exists",
        "is_file",
        "is_dir",
        "is_symlink",
        "iterdir",
        "glob",
        "rglob",
        "resolve",
        "absolute",
        "touch",
        "mkdir",
        "unlink",
        "rmdir",
        "readlink",
        "chmod",
        "lchmod",
        "symlink_to",
        "hardlink_to",
    ):
        _patch(Path, name)
    for name in ("rename", "replace"):
        _patch(Path, name, positions=(0, 1), keywords=("target",))
    _ORIGINALS["subprocess.Popen.__init__"] = subprocess.Popen.__init__
    subprocess.Popen.__init__ = _guarded_popen_init(subprocess.Popen.__init__)
    PHASE411_GUARD_INSTALLED = True


if os.environ.get("PHASE411_DENY_OPEN_SENTINEL") == "1":
    install_phase411_deny_open_guard()
