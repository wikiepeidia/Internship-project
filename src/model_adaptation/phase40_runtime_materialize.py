"""Fail-closed materialization of the Phase 40 runtime byte authority.

The release-authority producer deliberately refuses to discover an ambient
Python installation.  This module is the one production bridge from the
current, already-trained Windows environment into that explicit API.  It
copies the interpreter and every dependency into two separately-built,
closed trees, runs a staged-runtime smoke, and accepts the result only when the
two capture passes are byte-identical.  This is a closed Python package/prefix
byte closure, not a claim that the host OS, GPU, CUDA driver, network, or
process sandbox is captured.

The command never accepts an output path.  Repository outputs and staging child
names are fixed so an operator cannot silently redirect an authority.
"""

from __future__ import annotations

import argparse
from collections import deque
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import importlib.util
import json
import math
import os
from pathlib import Path, PurePosixPath, PureWindowsPath
import platform
import re
import secrets
import stat
import subprocess
import sys
import sysconfig
import tempfile
from types import MappingProxyType
from typing import Protocol

from packaging.markers import default_environment
from packaging.requirements import InvalidRequirement, Requirement
from packaging.version import InvalidVersion, Version

from src.model_adaptation import phase40_release_authorities as release


RUNTIME_AUTHORITY_RELATIVE_PATH = PurePosixPath(
    "data/models/phase40/runtime-dependency-authority.json"
)
MATERIALIZATION_RECEIPT_RELATIVE_PATH = PurePosixPath(
    "data/models/phase40/runtime-dependency-materialization-receipt.json"
)
MATERIALIZATION_COMPLETE_RELATIVE_PATH = PurePosixPath(
    "data/models/phase40/runtime-dependency-materialization-complete.json"
)
MATERIALIZATION_RECEIPT_SCHEMA_VERSION = (
    "phase40-runtime-dependency-materialization-receipt-v2"
)
MATERIALIZATION_COMPLETE_SCHEMA_VERSION = (
    "phase40-runtime-dependency-materialization-complete-v1"
)
STAGING_RECIPE_SCHEMA_VERSION = "phase40-runtime-dependency-staging-recipe-v3"
SMOKE_SCHEMA_VERSION = "phase40-runtime-staged-smoke-v2"
CAPTURE_ROOT_NAMES = ("capture-a", "capture-b")
PYTHON_RUNTIME_ROOT_NAME = "python-runtime"
DISTRIBUTIONS_ROOT_NAME = "distributions"

# These are evidence-fixed direct execution roots.  The recursive closure is
# resolved from their installed Requires-Dist metadata under the current
# marker environment; it is not silently expanded to every ambient package.
FIXED_DIRECT_DISTRIBUTIONS = MappingProxyType(
    {
        "accelerate": "1.13.0",
        "bitsandbytes": "0.50.1",
        "gguf": "0.19.0",
        "huggingface-hub": "1.16.1",
        "llama-cpp-python": "0.3.23",
        "matplotlib": "3.11.1",
        "peft": "0.19.1",
        "scikit-learn": "1.8.0",
        "torch": "2.12.0+cu132",
        "transformers": "5.9.0",
        "underthesea": "9.5.0",
    }
)
_DIRECT_IMPORT_MODULES = MappingProxyType(
    {
        "accelerate": "accelerate",
        "bitsandbytes": "bitsandbytes",
        "gguf": "gguf",
        "huggingface-hub": "huggingface_hub",
        "llama-cpp-python": "llama_cpp",
        "matplotlib": "matplotlib",
        "peft": "peft",
        "scikit-learn": "sklearn",
        "torch": "torch",
        "transformers": "transformers",
        "underthesea": "underthesea",
    }
)
_SMOKE_CHECK_KEYS = frozenset(
    {
        "bitsandbytes_linear4bit",
        "bitsandbytes_nf4_roundtrip",
        "direct_imports",
        "matplotlib_agg_render",
        "sklearn_metrics",
        "staged_distribution_origins",
        "staged_module_origins",
        "torch_cuda_available",
        "underthesea_word_tokenize",
    }
)
_HOST_PREREQUISITE_KEYS = frozenset(
    {
        "binding",
        "cuda_capabilities",
        "cuda_device_count",
        "cuda_device_name_sha256",
        "cuda_runtime",
        "machine",
        "os_name",
        "sys_platform",
    }
)
_SMOKE_PASSTHROUGH_ENV_KEYS = frozenset(
    {
        "COMSPEC",
        "CUDA_VISIBLE_DEVICES",
        "NVIDIA_VISIBLE_DEVICES",
        "PATHEXT",
        "SYSTEMROOT",
        "WINDIR",
    }
)
IMPORT_ORIGIN_OVERRIDES = MappingProxyType(
    {
        "llama-cpp-python": "llama_cpp",
        "markdown-it-py": "markdown_it",
        "pyyaml": "yaml",
    }
)
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_PERSONAL_ABSOLUTE_PATH_RE = re.compile(
    r"(?i)(?:^[A-Z]:[\\/]|^\\\\|^/(?:home|Users)/|[A-Z]:[\\/]Users[\\/])"
)
_SAFE_ROOT_NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
_COPY_CHUNK_BYTES = 4 * 1024 * 1024


class RuntimeMaterializationError(RuntimeError):
    """The live runtime cannot be materialized without weakening the contract."""


class DistributionLike(Protocol):
    """Narrow importlib.metadata surface consumed by the materializer."""

    version: str
    files: Iterable[os.PathLike[str]] | None
    requires: Iterable[str] | None
    metadata: Mapping[str, str]

    def locate_file(self, path: os.PathLike[str]) -> os.PathLike[str]: ...


@dataclass(frozen=True, slots=True)
class MetadataHooks:
    distribution: Callable[[str], DistributionLike]
    packages_distributions: Callable[[], Mapping[str, Sequence[str]]]
    find_spec: Callable[[str], object | None]
    marker_environment: Callable[[], Mapping[str, str]]


@dataclass(frozen=True, slots=True)
class PythonSource:
    implementation: str
    version: str
    cache_tag: str
    abi_flags: str
    platform: str
    prefix: Path
    site_packages: Path
    executable: Path


@dataclass(frozen=True, slots=True)
class FileSnapshot:
    relative_path: str
    bytes: int
    sha256: str


@dataclass(frozen=True, slots=True)
class DistributionSource:
    name: str
    version: str
    distribution: DistributionLike
    requirements: tuple[str, ...]
    requested_extras: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class SourceFile:
    owner: str
    source: Path
    staged_relative_path: Path


@dataclass(frozen=True, slots=True)
class PreparedDistribution:
    name: str
    version: str
    files: tuple[SourceFile, ...]
    import_origin_relative_path: Path


@dataclass(frozen=True, slots=True)
class DependencyResolution:
    distributions: tuple[DistributionSource, ...]
    marker_environment: Mapping[str, str]

    @property
    def expected_versions(self) -> dict[str, str]:
        return {item.name: item.version for item in self.distributions}


@dataclass(frozen=True, slots=True)
class StagedCapture:
    capture_id: str
    root: Path
    python: release.PythonCaptureInput
    distributions: tuple[release.DistributionCaptureInput, ...]
    snapshots: tuple[FileSnapshot, ...]
    smoke: Mapping[str, object]


SmokeRunner = Callable[
    [StagedCapture, Mapping[str, str], PythonSource], Mapping[str, object]
]


@dataclass(frozen=True, slots=True)
class _MaterializationServices:
    metadata: MetadataHooks
    discover_python: Callable[[], PythonSource]
    path_is_redirecting: Callable[[Path], bool]
    smoke_runner: SmokeRunner
    now: Callable[[], datetime]
    capture_authority: Callable[..., release.RuntimeDependencyAuthority]
    verify_authority: Callable[..., release.RuntimeDependencyAuthority]
    publication_hook: Callable[[str], None]


@dataclass(frozen=True, slots=True)
class MaterializationResult:
    authority: release.RuntimeDependencyAuthority
    authority_path: Path
    receipt: Mapping[str, object]
    receipt_path: Path
    completion: Mapping[str, object]
    completion_path: Path


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _canonical_json_bytes(value: object) -> bytes:
    _require_json_value(value)
    try:
        rendered = json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
    except (TypeError, ValueError) as exc:
        raise RuntimeMaterializationError("value is not canonical JSON data") from exc
    return rendered.encode("utf-8", errors="strict") + b"\n"


def _require_json_value(value: object, *, where: str = "$") -> None:
    if value is None or isinstance(value, (bool, int, str)):
        if isinstance(value, str) and "\x00" in value:
            raise RuntimeMaterializationError(f"NUL is forbidden at {where}")
        return
    if isinstance(value, float):
        if not math.isfinite(value):
            raise RuntimeMaterializationError(f"non-finite value at {where}")
        return
    if isinstance(value, Mapping):
        for key, child in value.items():
            if not isinstance(key, str) or not key:
                raise RuntimeMaterializationError(
                    f"JSON keys must be non-empty text at {where}"
                )
            _require_json_value(child, where=f"{where}.{key}")
        return
    if isinstance(value, (list, tuple)):
        for index, child in enumerate(value):
            _require_json_value(child, where=f"{where}[{index}]")
        return
    raise RuntimeMaterializationError(
        f"unsupported JSON value at {where}: {type(value).__name__}"
    )


def _reject_absolute_path_leakage(value: object, *, where: str = "receipt") -> None:
    if isinstance(value, Mapping):
        for key, child in value.items():
            _reject_absolute_path_leakage(child, where=f"{where}.{key}")
        return
    if isinstance(value, (list, tuple)):
        for index, child in enumerate(value):
            _reject_absolute_path_leakage(child, where=f"{where}[{index}]")
        return
    if not isinstance(value, str):
        return
    if (
        _PERSONAL_ABSOLUTE_PATH_RE.search(value)
        or PureWindowsPath(value).is_absolute()
        or PurePosixPath(value).is_absolute()
    ):
        raise RuntimeMaterializationError(f"{where} leaks an absolute path")


def _path_key(path: Path) -> str:
    return os.path.normcase(os.path.abspath(os.fspath(path)))


def _absolute_input(
    path: Path,
    *,
    where: str,
    allow_normalized_traversal: bool = False,
) -> Path:
    candidate = Path(path)
    if not candidate.is_absolute():
        raise RuntimeMaterializationError(f"{where} must be absolute")
    if not allow_normalized_traversal and ".." in candidate.parts:
        raise RuntimeMaterializationError(f"{where} contains lexical traversal")
    return Path(os.path.abspath(os.fspath(candidate)))


def _is_within(path: Path, root: Path) -> bool:
    try:
        return os.path.commonpath((_path_key(path), _path_key(root))) == _path_key(root)
    except ValueError:
        return False


def _require_disjoint(first: Path, second: Path, *, where: str) -> None:
    if _is_within(first, second) or _is_within(second, first):
        raise RuntimeMaterializationError(f"{where} roots must be disjoint")


def _default_path_is_redirecting(path: Path) -> bool:
    candidate = Path(path)
    try:
        if candidate.is_symlink():
            return True
        attributes = getattr(candidate.lstat(), "st_file_attributes", 0)
    except OSError:
        return False
    return bool(attributes & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400))


def _existing_ancestry(path: Path) -> tuple[Path, ...]:
    absolute = Path(os.path.abspath(os.fspath(path)))
    result: list[Path] = []
    current = absolute
    while True:
        if current.exists() or current.is_symlink():
            result.append(current)
        if current.parent == current:
            break
        current = current.parent
    return tuple(reversed(result))


def _require_safe_existing_directory(
    path: Path,
    *,
    where: str,
    services: _MaterializationServices,
) -> Path:
    candidate = _absolute_input(path, where=where)
    if not candidate.is_dir():
        raise RuntimeMaterializationError(f"{where} is not an existing directory")
    for component in _existing_ancestry(candidate):
        if services.path_is_redirecting(component):
            raise RuntimeMaterializationError(f"{where} ancestry is symlink/reparse")
    return candidate


def _require_safe_regular_file(
    path: Path,
    *,
    where: str,
    services: _MaterializationServices,
    allow_normalized_traversal: bool = False,
) -> Path:
    candidate = _absolute_input(
        path,
        where=where,
        allow_normalized_traversal=allow_normalized_traversal,
    )
    for component in _existing_ancestry(candidate):
        if services.path_is_redirecting(component):
            raise RuntimeMaterializationError(f"{where} ancestry is symlink/reparse")
    try:
        mode = candidate.lstat().st_mode
    except OSError as exc:
        raise RuntimeMaterializationError(f"{where} is missing") from exc
    if not stat.S_ISREG(mode):
        raise RuntimeMaterializationError(f"{where} is not a regular file")
    return candidate


def _normalize_name(value: str) -> str:
    try:
        return release.normalize_distribution_name(value)
    except Exception as exc:
        raise RuntimeMaterializationError("distribution name is invalid") from exc


def _require_version(value: object, *, where: str) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        raise RuntimeMaterializationError(f"{where} is not a canonical version")
    try:
        Version(value)
    except InvalidVersion as exc:
        raise RuntimeMaterializationError(f"{where} is invalid") from exc
    return value


def _metadata_name(distribution: DistributionLike) -> str:
    try:
        value = distribution.metadata["Name"]
    except (KeyError, TypeError) as exc:
        raise RuntimeMaterializationError("distribution metadata lacks Name") from exc
    if not isinstance(value, str):
        raise RuntimeMaterializationError("distribution metadata Name is malformed")
    return _normalize_name(value)


def _active_requirement(
    requirement: Requirement,
    *,
    marker_environment: Mapping[str, str],
    active_extras: Iterable[str],
) -> bool:
    if requirement.marker is None:
        return True
    extras = ("", *tuple(sorted(set(active_extras))))
    for extra in extras:
        environment = dict(marker_environment)
        environment["extra"] = extra
        try:
            if requirement.marker.evaluate(environment=environment):
                return True
        except Exception as exc:
            raise RuntimeMaterializationError(
                f"failed to evaluate dependency marker for {requirement.name}"
            ) from exc
    return False


def resolve_dependency_closure(
    *, metadata: MetadataHooks
) -> DependencyResolution:
    """Resolve the exact installed no-ambient dependency closure."""

    marker_environment = dict(metadata.marker_environment())
    if not marker_environment or any(
        not isinstance(key, str)
        or not key
        or not isinstance(value, str)
        or "\x00" in value
        for key, value in marker_environment.items()
    ):
        raise RuntimeMaterializationError("dependency marker environment is malformed")
    marker_environment["extra"] = ""

    requested_extras: dict[str, set[str]] = {
        name: set() for name in FIXED_DIRECT_DISTRIBUTIONS
    }
    queue: deque[str] = deque(sorted(FIXED_DIRECT_DISTRIBUTIONS))
    resolved: dict[str, DistributionSource] = {}
    processed_extras: dict[str, frozenset[str]] = {}

    while queue:
        requested_name = _normalize_name(queue.popleft())
        extras = frozenset(requested_extras.setdefault(requested_name, set()))
        if processed_extras.get(requested_name) == extras:
            continue
        try:
            distribution = metadata.distribution(requested_name)
        except Exception as exc:
            raise RuntimeMaterializationError(
                f"required distribution is unavailable: {requested_name}"
            ) from exc
        observed_name = _metadata_name(distribution)
        if observed_name != requested_name:
            raise RuntimeMaterializationError(
                f"distribution lookup drifted: {requested_name} -> {observed_name}"
            )
        version = _require_version(
            distribution.version,
            where=f"{requested_name} installed version",
        )
        if requested_name in FIXED_DIRECT_DISTRIBUTIONS and version != (
            FIXED_DIRECT_DISTRIBUTIONS[requested_name]
        ):
            raise RuntimeMaterializationError(
                f"fixed direct distribution version drifted: {requested_name}"
            )

        raw_requirements = tuple(distribution.requires or ())
        if any(not isinstance(item, str) or not item for item in raw_requirements):
            raise RuntimeMaterializationError(
                f"{requested_name} Requires-Dist metadata is malformed"
            )
        for raw in raw_requirements:
            try:
                requirement = Requirement(raw)
            except InvalidRequirement as exc:
                raise RuntimeMaterializationError(
                    f"{requested_name} has invalid Requires-Dist metadata"
                ) from exc
            if requirement.url is not None:
                raise RuntimeMaterializationError(
                    f"{requested_name} has a non-portable direct-URL dependency"
                )
            if not _active_requirement(
                requirement,
                marker_environment=marker_environment,
                active_extras=extras,
            ):
                continue
            child = _normalize_name(requirement.name)
            try:
                child_distribution = metadata.distribution(child)
                child_name = _metadata_name(child_distribution)
                child_version = _require_version(
                    child_distribution.version,
                    where=f"{child} installed version",
                )
            except Exception as exc:
                if isinstance(exc, RuntimeMaterializationError):
                    raise
                raise RuntimeMaterializationError(
                    f"dependency is unavailable: {requested_name} -> {child}"
                ) from exc
            if child_name != child or (
                requirement.specifier
                and not requirement.specifier.contains(child_version, prereleases=True)
            ):
                raise RuntimeMaterializationError(
                    f"installed dependency does not satisfy {requested_name}: {requirement}"
                )
            child_extras = requested_extras.setdefault(child, set())
            before = frozenset(child_extras)
            child_extras.update(requirement.extras)
            if child not in resolved or before != frozenset(child_extras):
                queue.append(child)

        resolved[requested_name] = DistributionSource(
            name=requested_name,
            version=version,
            distribution=distribution,
            requirements=tuple(sorted(raw_requirements)),
            requested_extras=tuple(sorted(extras)),
        )
        processed_extras[requested_name] = extras

    if set(FIXED_DIRECT_DISTRIBUTIONS) - set(resolved):
        raise RuntimeMaterializationError("fixed direct distribution closure is incomplete")
    return DependencyResolution(
        distributions=tuple(resolved[name] for name in sorted(resolved)),
        marker_environment=MappingProxyType(dict(sorted(marker_environment.items()))),
    )


def _default_metadata_hooks() -> MetadataHooks:
    return MetadataHooks(
        distribution=importlib.metadata.distribution,  # type: ignore[arg-type]
        packages_distributions=importlib.metadata.packages_distributions,
        find_spec=importlib.util.find_spec,
        marker_environment=default_environment,
    )


def _discover_live_python() -> PythonSource:
    if sys.prefix != sys.base_prefix:
        raise RuntimeMaterializationError(
            "runtime authority must be captured from a base interpreter, not a venv"
        )
    purelib = Path(sysconfig.get_path("purelib"))
    platlib = Path(sysconfig.get_path("platlib"))
    if _path_key(purelib) != _path_key(platlib):
        raise RuntimeMaterializationError(
            "split purelib/platlib layouts require an explicit new staging recipe"
        )
    return PythonSource(
        implementation=sys.implementation.name,
        version=platform.python_version(),
        cache_tag=str(sys.implementation.cache_tag or ""),
        abi_flags=str(getattr(sys, "abiflags", "")),
        platform=sys.platform,
        prefix=Path(sys.base_prefix),
        site_packages=purelib,
        executable=Path(sys.executable),
    )


def _safe_relative_path(path: Path, root: Path, *, where: str) -> Path:
    if not _is_within(path, root):
        raise RuntimeMaterializationError(f"{where} escapes its trusted root")
    try:
        relative = path.relative_to(root)
    except ValueError as exc:
        raise RuntimeMaterializationError(f"{where} escapes its trusted root") from exc
    if (
        relative.is_absolute()
        or not relative.parts
        or any(
            not part
            or part in {".", ".."}
            or "\x00" in part
            or ":" in part
            or "\\" in part
            for part in relative.parts
        )
    ):
        raise RuntimeMaterializationError(f"{where} is not a safe relative path")
    return relative


def _staged_distribution_path(
    source: Path,
    *,
    python: PythonSource,
) -> Path:
    if _is_within(source, python.site_packages):
        relative = _safe_relative_path(
            source,
            python.site_packages,
            where="site-packages distribution file",
        )
        return Path("site-packages") / relative
    if _is_within(source, python.prefix):
        relative = _safe_relative_path(
            source,
            python.prefix,
            where="prefix-relative distribution file",
        )
        return Path("python-prefix") / relative
    raise RuntimeMaterializationError(
        "distribution metadata file escapes both site-packages and Python prefix"
    )


def _preferred_import_module(
    distribution_name: str,
    *,
    metadata: MetadataHooks,
) -> str:
    candidates = {
        module
        for module, owners in metadata.packages_distributions().items()
        if isinstance(module, str)
        and module
        and isinstance(owners, Sequence)
        and any(
            isinstance(owner, str)
            and _normalize_name(owner) == distribution_name
            for owner in owners
        )
    }
    override = IMPORT_ORIGIN_OVERRIDES.get(distribution_name)
    preferred = override or distribution_name.replace("-", "_")
    if preferred not in candidates:
        if len(candidates) != 1:
            raise RuntimeMaterializationError(
                f"{distribution_name} import origin is absent or ambiguous"
            )
        preferred = next(iter(candidates))
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", preferred):
        raise RuntimeMaterializationError(
            f"{distribution_name} import module name is unsafe"
        )
    return preferred


def prepare_distribution_sources(
    resolution: DependencyResolution,
    python: PythonSource,
    *,
    metadata: MetadataHooks,
    services: _MaterializationServices,
) -> tuple[PreparedDistribution, ...]:
    """Bind metadata file ownership and safe staged paths before any write."""

    source_owners: dict[str, str] = {}
    physical_owners: dict[tuple[int, int], str] = {}
    prepared: list[PreparedDistribution] = []
    packages_mapping = metadata.packages_distributions()
    stable_metadata = MetadataHooks(
        distribution=metadata.distribution,
        packages_distributions=lambda: packages_mapping,
        find_spec=metadata.find_spec,
        marker_environment=metadata.marker_environment,
    )
    for item in resolution.distributions:
        raw_files = item.distribution.files
        if raw_files is None:
            raise RuntimeMaterializationError(f"{item.name} has no installed file inventory")
        files: list[SourceFile] = []
        destination_keys: set[str] = set()
        owner_source_keys: set[str] = set()
        for declared in raw_files:
            try:
                located = Path(item.distribution.locate_file(declared))
            except Exception as exc:
                raise RuntimeMaterializationError(
                    f"{item.name} cannot locate a declared file"
                ) from exc
            source = _require_safe_regular_file(
                located,
                where=f"{item.name} declared file",
                services=services,
                allow_normalized_traversal=True,
            )
            if not _is_within(source, python.prefix):
                raise RuntimeMaterializationError(
                    f"{item.name} declared file escapes the Python prefix"
                )
            source_key = _path_key(source)
            if source_key in owner_source_keys:
                # Some installed RECORD inventories expose the same entry once
                # with POSIX separators and once with Windows separators.  An
                # exact same-source alias is one file, not two ownership claims.
                continue
            existing_owner = source_owners.get(source_key)
            if existing_owner is not None:
                raise RuntimeMaterializationError(
                    f"distribution file ownership collides: {existing_owner}/{item.name}"
                )
            source_stat = source.lstat()
            physical_identity = (int(source_stat.st_dev), int(source_stat.st_ino))
            if physical_identity != (0, 0):
                physical_owner = physical_owners.get(physical_identity)
                if physical_owner is not None:
                    raise RuntimeMaterializationError(
                        "distribution physical file ownership collides: "
                        f"{physical_owner}/{item.name}"
                    )
                physical_owners[physical_identity] = item.name
            staged = _staged_distribution_path(source, python=python)
            staged_key = staged.as_posix().casefold()
            if staged_key in destination_keys:
                raise RuntimeMaterializationError(
                    f"{item.name} staged distribution path collides"
                )
            owner_source_keys.add(source_key)
            source_owners[source_key] = item.name
            destination_keys.add(staged_key)
            files.append(
                SourceFile(
                    owner=item.name,
                    source=source,
                    staged_relative_path=staged,
                )
            )
        if not files:
            raise RuntimeMaterializationError(f"{item.name} file inventory is empty")

        module = _preferred_import_module(item.name, metadata=stable_metadata)
        try:
            spec = stable_metadata.find_spec(module)
        except Exception as exc:
            raise RuntimeMaterializationError(
                f"{item.name} import spec lookup failed"
            ) from exc
        origin_text = getattr(spec, "origin", None)
        if not isinstance(origin_text, str) or origin_text in {"built-in", "frozen"}:
            raise RuntimeMaterializationError(
                f"{item.name} import origin is missing or non-file"
            )
        origin = _require_safe_regular_file(
            Path(origin_text),
            where=f"{item.name} import origin",
            services=services,
        )
        origin_key = _path_key(origin)
        matching = tuple(
            source_file
            for source_file in files
            if _path_key(source_file.source) == origin_key
        )
        if len(matching) != 1:
            raise RuntimeMaterializationError(
                f"{item.name} import origin is not uniquely owned by its inventory"
            )
        prepared.append(
            PreparedDistribution(
                name=item.name,
                version=item.version,
                files=tuple(
                    sorted(files, key=lambda value: value.staged_relative_path.as_posix())
                ),
                import_origin_relative_path=matching[0].staged_relative_path,
            )
        )
    return tuple(sorted(prepared, key=lambda value: value.name))


def _iter_regular_tree_files(
    root: Path,
    *,
    excluded_subtrees: Sequence[Path],
    services: _MaterializationServices,
) -> tuple[Path, ...]:
    exclusions = tuple(_path_key(path) for path in excluded_subtrees)
    result: list[Path] = []
    seen_relative: set[str] = set()

    def excluded(path: Path) -> bool:
        key = _path_key(path)
        return any(key == item or key.startswith(item + os.sep) for item in exclusions)

    def visit(directory: Path) -> None:
        if excluded(directory):
            return
        try:
            entries = sorted(
                os.scandir(directory),
                key=lambda entry: (entry.name.casefold(), entry.name),
            )
        except OSError as exc:
            raise RuntimeMaterializationError(
                "failed to enumerate Python runtime tree"
            ) from exc
        for entry in entries:
            candidate = Path(entry.path)
            if excluded(candidate):
                continue
            if entry.is_symlink() or services.path_is_redirecting(candidate):
                raise RuntimeMaterializationError(
                    "Python runtime tree contains a symlink/reparse entry"
                )
            try:
                if entry.is_dir(follow_symlinks=False):
                    visit(candidate)
                    continue
                if not entry.is_file(follow_symlinks=False):
                    raise RuntimeMaterializationError(
                        "Python runtime tree contains a non-regular entry"
                    )
            except OSError as exc:
                raise RuntimeMaterializationError(
                    "Python runtime tree entry changed during enumeration"
                ) from exc
            relative = _safe_relative_path(
                candidate,
                root,
                where="Python runtime file",
            )
            key = relative.as_posix().casefold()
            if key in seen_relative:
                raise RuntimeMaterializationError(
                    "Python runtime contains a case-insensitive path collision"
                )
            seen_relative.add(key)
            result.append(candidate)

    visit(root)
    return tuple(result)


def _ensure_directory(
    root: Path,
    directory: Path,
    *,
    services: _MaterializationServices,
) -> None:
    if not _is_within(directory, root):
        raise RuntimeMaterializationError("destination directory escapes staging root")
    relative = directory.relative_to(root)
    current = root
    for component in relative.parts:
        current = current / component
        if current.exists() or current.is_symlink():
            if not current.is_dir() or services.path_is_redirecting(current):
                raise RuntimeMaterializationError(
                    "staging ancestry became non-directory or redirecting"
                )
            continue
        try:
            current.mkdir()
        except OSError as exc:
            raise RuntimeMaterializationError(
                "failed to create a staging directory"
            ) from exc
        if services.path_is_redirecting(current):
            raise RuntimeMaterializationError("new staging directory is redirecting")


def _hash_regular_file(
    path: Path,
    *,
    services: _MaterializationServices,
    where: str,
) -> tuple[int, str]:
    candidate = _require_safe_regular_file(path, where=where, services=services)
    digest = hashlib.sha256()
    total = 0
    try:
        with candidate.open("rb") as handle:
            while chunk := handle.read(_COPY_CHUNK_BYTES):
                total += len(chunk)
                digest.update(chunk)
    except OSError as exc:
        raise RuntimeMaterializationError(f"failed to hash {where}") from exc
    return total, digest.hexdigest()


def _copy_stable_file(
    source: Path,
    target: Path,
    *,
    stage_root: Path,
    relative_path: Path,
    services: _MaterializationServices,
) -> FileSnapshot:
    source = _require_safe_regular_file(
        source,
        where="copy source",
        services=services,
    )
    if not _is_within(target, stage_root):
        raise RuntimeMaterializationError("copy target escapes staging root")
    _ensure_directory(stage_root, target.parent, services=services)
    if target.exists() or target.is_symlink():
        raise RuntimeMaterializationError("copy target already exists")
    digest = hashlib.sha256()
    total = 0
    try:
        with source.open("rb") as reader, target.open("xb") as writer:
            while chunk := reader.read(_COPY_CHUNK_BYTES):
                digest.update(chunk)
                total += len(chunk)
                writer.write(chunk)
            writer.flush()
            os.fsync(writer.fileno())
    except OSError as exc:
        raise RuntimeMaterializationError("stable file copy failed") from exc
    source_bytes, source_sha = _hash_regular_file(
        source,
        services=services,
        where="copy source after copy",
    )
    target_bytes, target_sha = _hash_regular_file(
        target,
        services=services,
        where="copy target after copy",
    )
    copied_sha = digest.hexdigest()
    if (
        source_bytes != total
        or target_bytes != total
        or source_sha != copied_sha
        or target_sha != copied_sha
    ):
        raise RuntimeMaterializationError("source or destination drifted during copy")
    relative_text = relative_path.as_posix()
    if PurePosixPath(relative_text).as_posix() != relative_text:
        raise RuntimeMaterializationError("copied relative path is noncanonical")
    return FileSnapshot(relative_text, total, copied_sha)


def _snapshot_key(snapshot: FileSnapshot) -> tuple[str, int, str]:
    return snapshot.relative_path, snapshot.bytes, snapshot.sha256


def _verify_stage_snapshot(
    stage: StagedCapture,
    *,
    services: _MaterializationServices,
) -> None:
    observed: list[FileSnapshot] = []
    files = _iter_regular_tree_files(
        stage.root,
        excluded_subtrees=(),
        services=services,
    )
    for path in files:
        relative = _safe_relative_path(path, stage.root, where="staged snapshot file")
        size, digest = _hash_regular_file(
            path,
            services=services,
            where="staged snapshot file",
        )
        observed.append(FileSnapshot(relative.as_posix(), size, digest))
    expected_keys = tuple(sorted(map(_snapshot_key, stage.snapshots)))
    observed_keys = tuple(sorted(map(_snapshot_key, observed)))
    if observed_keys != expected_keys:
        raise RuntimeMaterializationError("staged tree inventory or bytes drifted")


def _stage_one_capture(
    *,
    capture_id: str,
    root: Path,
    python: PythonSource,
    distributions: Sequence[PreparedDistribution],
    expected_versions: Mapping[str, str],
    services: _MaterializationServices,
) -> StagedCapture:
    if capture_id not in CAPTURE_ROOT_NAMES or root.name != capture_id:
        raise RuntimeMaterializationError("capture root identity is not fixed")
    if root.exists() or root.is_symlink():
        raise RuntimeMaterializationError(f"fixed staging child already exists: {capture_id}")
    try:
        root.mkdir()
    except OSError as exc:
        raise RuntimeMaterializationError("failed to create fixed staging child") from exc
    if services.path_is_redirecting(root):
        raise RuntimeMaterializationError("fixed staging child is redirecting")

    python_root = root / PYTHON_RUNTIME_ROOT_NAME
    distributions_root = root / DISTRIBUTIONS_ROOT_NAME
    python_root.mkdir()
    distributions_root.mkdir()
    snapshots: list[FileSnapshot] = []
    package_owned = {
        _path_key(file.source)
        for distribution in distributions
        for file in distribution.files
    }
    runtime_sources = _iter_regular_tree_files(
        python.prefix,
        excluded_subtrees=(python.site_packages,),
        services=services,
    )
    for source in runtime_sources:
        if _path_key(source) in package_owned:
            continue
        relative = _safe_relative_path(
            source,
            python.prefix,
            where="Python runtime source",
        )
        target = python_root / relative
        snapshots.append(
            _copy_stable_file(
                source,
                target,
                stage_root=root,
                relative_path=Path(PYTHON_RUNTIME_ROOT_NAME) / relative,
                services=services,
            )
        )

    executable_relative = _safe_relative_path(
        python.executable,
        python.prefix,
        where="Python executable",
    )
    staged_executable = python_root / executable_relative
    if not staged_executable.is_file():
        raise RuntimeMaterializationError(
            "Python executable was not copied into the closed runtime tree"
        )
    distribution_inputs: list[release.DistributionCaptureInput] = []
    for distribution in distributions:
        install_root = distributions_root / distribution.name
        if install_root.exists() or install_root.is_symlink():
            raise RuntimeMaterializationError("dedicated distribution root collides")
        install_root.mkdir()
        declared: list[Path] = []
        for source_file in distribution.files:
            target = install_root / source_file.staged_relative_path
            snapshots.append(
                _copy_stable_file(
                    source_file.source,
                    target,
                    stage_root=root,
                    relative_path=(
                        Path(DISTRIBUTIONS_ROOT_NAME)
                        / distribution.name
                        / source_file.staged_relative_path
                    ),
                    services=services,
                )
            )
            declared.append(source_file.staged_relative_path)
        distribution_inputs.append(
            release.DistributionCaptureInput(
                name=distribution.name,
                version=distribution.version,
                install_root=install_root,
                import_origin=distribution.import_origin_relative_path,
                declared_files=tuple(sorted(declared, key=lambda path: path.as_posix())),
            )
        )

    provisional = StagedCapture(
        capture_id=capture_id,
        root=root,
        python=release.PythonCaptureInput(
            implementation=python.implementation,
            version=python.version,
            cache_tag=python.cache_tag,
            abi_flags=python.abi_flags,
            platform=python.platform,
            executable_root=python_root,
            executable=executable_relative,
        ),
        distributions=tuple(sorted(distribution_inputs, key=lambda item: item.name)),
        snapshots=tuple(sorted(snapshots, key=lambda item: item.relative_path)),
        smoke=MappingProxyType({}),
    )
    _verify_stage_snapshot(provisional, services=services)
    smoke = dict(services.smoke_runner(provisional, expected_versions, python))
    _validate_smoke_result(
        smoke,
        expected_versions=expected_versions,
        expected_python_version=python.version,
    )
    staged = StagedCapture(
        capture_id=provisional.capture_id,
        root=provisional.root,
        python=provisional.python,
        distributions=provisional.distributions,
        snapshots=provisional.snapshots,
        smoke=MappingProxyType(smoke),
    )
    _verify_stage_snapshot(staged, services=services)
    return staged


def _validate_smoke_result(
    smoke: Mapping[str, object],
    *,
    expected_versions: Mapping[str, str],
    expected_python_version: str,
) -> None:
    expected_keys = {
        "schema_version",
        "status",
        "python",
        "packages",
        "checks",
        "host_prerequisites",
    }
    if set(smoke) != expected_keys:
        raise RuntimeMaterializationError("staged smoke result fields differ from schema")
    if (
        smoke.get("schema_version") != SMOKE_SCHEMA_VERSION
        or smoke.get("status") != "passed"
    ):
        raise RuntimeMaterializationError("staged runtime smoke did not pass")
    packages = smoke.get("packages")
    checks = smoke.get("checks")
    if packages != dict(sorted(expected_versions.items())):
        raise RuntimeMaterializationError("staged smoke package closure drifted")
    if smoke.get("python") != expected_python_version:
        raise RuntimeMaterializationError("staged smoke Python version drifted")
    if (
        not isinstance(checks, Mapping)
        or set(checks) != _SMOKE_CHECK_KEYS
        or any(value is not True for value in checks.values())
    ):
        raise RuntimeMaterializationError("staged smoke checks are incomplete")
    prerequisites = smoke.get("host_prerequisites")
    if (
        not isinstance(prerequisites, Mapping)
        or set(prerequisites) != _HOST_PREREQUISITE_KEYS
        or prerequisites.get("binding") != "observed-not-byte-bound"
        or not isinstance(prerequisites.get("os_name"), str)
        or not prerequisites.get("os_name")
        or not isinstance(prerequisites.get("sys_platform"), str)
        or not prerequisites.get("sys_platform")
        or not isinstance(prerequisites.get("machine"), str)
        or not prerequisites.get("machine")
        or not isinstance(prerequisites.get("cuda_runtime"), str)
        or not prerequisites.get("cuda_runtime")
        or not isinstance(prerequisites.get("cuda_device_count"), int)
        or isinstance(prerequisites.get("cuda_device_count"), bool)
        or int(prerequisites.get("cuda_device_count", 0)) <= 0
    ):
        raise RuntimeMaterializationError("staged smoke host prerequisites drifted")
    names = prerequisites.get("cuda_device_name_sha256")
    capabilities = prerequisites.get("cuda_capabilities")
    count = int(prerequisites.get("cuda_device_count", 0))
    if (
        not isinstance(names, list)
        or len(names) != count
        or any(not isinstance(item, str) or not _SHA256_RE.fullmatch(item) for item in names)
        or not isinstance(capabilities, list)
        or len(capabilities) != count
        or any(
            not isinstance(item, str) or not re.fullmatch(r"[0-9]+\.[0-9]+", item)
            for item in capabilities
        )
    ):
        raise RuntimeMaterializationError("staged smoke CUDA prerequisites drifted")
    _reject_absolute_path_leakage(smoke, where="staged smoke result")


_STAGED_SMOKE_PROGRAM = r"""
import hashlib
import importlib
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import sys

stage = Path(sys.argv[1])
expected = json.loads(sys.argv[2])
live_prefix = Path(sys.argv[3])
dist_root = stage / "distributions"
roots = [str(dist_root / name / "site-packages") for name in sorted(expected)]
sys.path[:0] = roots

def within(path, root):
    try:
        candidate = os.path.abspath(path)
        trusted = os.path.abspath(root)
        return os.path.commonpath((candidate, trusted)) == trusted
    except ValueError:
        return False

for entry in sys.path:
    if entry and within(entry, live_prefix) and not within(entry, stage):
        raise SystemExit("live-python-path-leak")
observed = {}
distribution_origins_staged = True
for name in sorted(expected):
    distribution = importlib.metadata.distribution(name)
    if not within(distribution.locate_file(""), stage):
        raise SystemExit("live-distribution-path-leak")
    observed[name] = distribution.version
if observed != expected:
    raise SystemExit("package-version-drift")
modules = {
    "accelerate": "accelerate",
    "bitsandbytes": "bitsandbytes",
    "gguf": "gguf",
    "huggingface-hub": "huggingface_hub",
    "llama-cpp-python": "llama_cpp",
    "matplotlib": "matplotlib",
    "peft": "peft",
    "scikit-learn": "sklearn",
    "torch": "torch",
    "transformers": "transformers",
    "underthesea": "underthesea",
}
loaded = {name: importlib.import_module(module) for name, module in modules.items()}
module_origins_staged = True
for module in loaded.values():
    origin = getattr(module, "__file__", None)
    if not isinstance(origin, str) or not within(origin, stage):
        raise SystemExit("live-module-path-leak")
torch = loaded["torch"]
bitsandbytes = loaded["bitsandbytes"]
underthesea = loaded["underthesea"]
sklearn_metrics = importlib.import_module("sklearn.metrics")
matplotlib = loaded["matplotlib"]
nf4_ok = False
if torch.cuda.is_available():
    values = torch.linspace(-1.0, 1.0, 4096, device="cuda", dtype=torch.float16).reshape(64, 64)
    quantized, quantization_state = bitsandbytes.functional.quantize_4bit(
        values,
        quant_type="nf4",
        compress_statistics=True,
    )
    restored = bitsandbytes.functional.dequantize_4bit(quantized, quantization_state)
    torch.cuda.synchronize()
    nf4_ok = tuple(restored.shape) == (64, 64) and bool(torch.isfinite(restored).all().item())
metrics_ok = (
    abs(float(sklearn_metrics.accuracy_score([0, 1, 1], [0, 1, 0])) - (2.0 / 3.0)) < 1e-12
    and sklearn_metrics.confusion_matrix([0, 1, 1], [0, 1, 0]).tolist()
    == [[1, 0], [1, 1]]
)
matplotlib.use("Agg", force=True)
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure
figure = Figure(figsize=(1.0, 1.0), dpi=24)
canvas = FigureCanvasAgg(figure)
axes = figure.subplots()
axes.plot([0, 1], [0, 1])
render_path = Path(os.environ["TEMP"]) / "phase40-runtime-smoke.png"
canvas.print_png(render_path)
matplotlib_ok = render_path.is_file() and render_path.stat().st_size > 0
render_path.unlink()
device_count = int(torch.cuda.device_count())
device_name_hashes = []
device_capabilities = []
for index in range(device_count):
    name = str(torch.cuda.get_device_name(index))
    device_name_hashes.append(hashlib.sha256(name.encode("utf-8", errors="strict")).hexdigest())
    major, minor = torch.cuda.get_device_capability(index)
    device_capabilities.append(f"{major}.{minor}")
checks = {
    "direct_imports": len(loaded) == len(modules),
    "staged_module_origins": module_origins_staged,
    "staged_distribution_origins": distribution_origins_staged,
    "torch_cuda_available": bool(torch.cuda.is_available()),
    "bitsandbytes_linear4bit": isinstance(getattr(bitsandbytes.nn, "Linear4bit", None), type),
    "bitsandbytes_nf4_roundtrip": nf4_ok,
    "underthesea_word_tokenize": bool(underthesea.word_tokenize("xin chào", format="text")),
    "sklearn_metrics": metrics_ok,
    "matplotlib_agg_render": matplotlib_ok,
}
if not all(checks.values()):
    raise SystemExit("runtime-check-failed")
payload = {
    "schema_version": "phase40-runtime-staged-smoke-v2",
    "status": "passed",
    "python": ".".join(map(str, sys.version_info[:3])),
    "packages": observed,
    "checks": checks,
    "host_prerequisites": {
        "binding": "observed-not-byte-bound",
        "os_name": os.name,
        "sys_platform": sys.platform,
        "machine": platform.machine(),
        "cuda_runtime": str(torch.version.cuda or ""),
        "cuda_device_count": device_count,
        "cuda_device_name_sha256": device_name_hashes,
        "cuda_capabilities": device_capabilities,
    },
}
print("PHASE40_RUNTIME_SMOKE=" + json.dumps(payload, sort_keys=True, separators=(",", ":")))
""".strip()


def _build_smoke_environment(
    *,
    executable: Path,
    temporary: Path,
    source_environment: Mapping[str, str],
) -> dict[str, str]:
    """Build the exact documented allowlist used by the staged smoke.

    Offline library flags are configuration only.  They are not represented as
    network isolation and the receipt explicitly records that limitation.
    """

    by_upper = {key.upper(): (key, value) for key, value in source_environment.items()}
    environment = {
        original: value
        for key in sorted(_SMOKE_PASSTHROUGH_ENV_KEYS)
        if (entry := by_upper.get(key)) is not None
        for original, value in (entry,)
    }
    if os.name == "nt":
        system_root_text = next(
            (
                value
                for key, value in environment.items()
                if key.upper() in {"SYSTEMROOT", "WINDIR"}
            ),
            r"C:\Windows",
        )
        system_root = Path(system_root_text)
        environment["PATH"] = os.pathsep.join(
            (
                os.fspath(executable.parent),
                os.fspath(executable.parent / "DLLs"),
                os.fspath(system_root / "System32"),
                os.fspath(system_root),
            )
        )
    else:
        environment["PATH"] = os.fspath(executable.parent)
    environment.update(
        {
            "HF_HUB_OFFLINE": "1",
            "TRANSFORMERS_OFFLINE": "1",
            "TOKENIZERS_PARALLELISM": "false",
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONNOUSERSITE": "1",
            "HF_HOME": os.fspath(temporary / "hf"),
            "MPLCONFIGDIR": os.fspath(temporary / "mpl"),
            # Torch 2.12 resolves its Inductor cache while importing through
            # bitsandbytes/PEFT.  A username-free strict environment otherwise
            # makes getpass fail mid-import and leaves torch._dynamo partially
            # initialized.  Keep the cache inside the disposable smoke root;
            # never pass through a personal username or host cache path.
            "TORCHINDUCTOR_CACHE_DIR": os.fspath(temporary / "torch-inductor"),
            "XDG_CACHE_HOME": os.fspath(temporary / "xdg-cache"),
            "TEMP": os.fspath(temporary),
            "TMP": os.fspath(temporary),
        }
    )
    return environment


def _run_staged_smoke(
    stage: StagedCapture,
    expected_versions: Mapping[str, str],
    source_python: PythonSource,
) -> Mapping[str, object]:
    executable = stage.python.executable_root / stage.python.executable
    try:
        with tempfile.TemporaryDirectory(
            prefix=f".{stage.capture_id}-smoke-",
            dir=stage.root.parent,
        ) as temporary_text:
            temporary = Path(temporary_text)
            environment = _build_smoke_environment(
                executable=executable,
                temporary=temporary,
                source_environment=os.environ,
            )
            command = (
                os.fspath(executable),
                "-E",
                "-s",
                "-S",
                "-B",
                "-c",
                _STAGED_SMOKE_PROGRAM,
                os.fspath(stage.root),
                json.dumps(
                    dict(sorted(expected_versions.items())),
                    separators=(",", ":"),
                ),
                os.fspath(source_python.prefix),
            )
            completed = subprocess.run(
                command,
                cwd=temporary,
                env=environment,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=300,
                check=False,
                text=True,
                encoding="utf-8",
                errors="strict",
                creationflags=(
                    getattr(subprocess, "CREATE_NO_WINDOW", 0)
                    if os.name == "nt"
                    else 0
                ),
            )
    except (OSError, subprocess.SubprocessError, UnicodeError) as exc:
        raise RuntimeMaterializationError("staged runtime smoke could not execute") from exc
    except RuntimeError as exc:
        raise RuntimeMaterializationError("staged smoke temp cleanup failed") from exc
    if completed.returncode != 0:
        detail = _sha256_bytes(
            (completed.stdout + "\n" + completed.stderr).encode(
                "utf-8", errors="replace"
            )
        )
        raise RuntimeMaterializationError(
            f"staged runtime smoke failed (detail_sha256={detail})"
        )
    prefix = "PHASE40_RUNTIME_SMOKE="
    records = [line for line in completed.stdout.splitlines() if line.startswith(prefix)]
    if len(records) != 1:
        raise RuntimeMaterializationError("staged runtime smoke output is ambiguous")
    try:
        payload = json.loads(records[0][len(prefix) :])
    except json.JSONDecodeError as exc:
        raise RuntimeMaterializationError("staged runtime smoke output is invalid") from exc
    if not isinstance(payload, dict):
        raise RuntimeMaterializationError("staged runtime smoke output is malformed")
    return payload


def _utc_text(value: datetime) -> str:
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise RuntimeMaterializationError("clock must return timezone-aware datetime")
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _parse_utc(value: object, *, where: str) -> datetime:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise RuntimeMaterializationError(f"{where} is not canonical UTC text")
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise RuntimeMaterializationError(f"{where} is not a UTC timestamp") from exc
    if _utc_text(parsed) != value:
        raise RuntimeMaterializationError(f"{where} is noncanonical")
    return parsed


def _path_identity_sha256(path: Path) -> str:
    normalized = os.path.normcase(os.path.abspath(os.fspath(path))).replace("\\", "/")
    return _sha256_bytes(normalized.encode("utf-8", errors="strict"))


def _recipe_payload() -> dict[str, object]:
    return {
        "schema_version": STAGING_RECIPE_SCHEMA_VERSION,
        "capture_children": list(CAPTURE_ROOT_NAMES),
        "python_runtime_root": PYTHON_RUNTIME_ROOT_NAME,
        "distributions_root": DISTRIBUTIONS_ROOT_NAME,
        "direct_distributions": dict(sorted(FIXED_DIRECT_DISTRIBUTIONS.items())),
        "closure_policy": "requires-dist-fixed-point-current-markers-no-ambient-v2",
        "copy_policy": "two-live-discovery-copy-passes-exclusive-stable-copy-v2",
        "python_exclusions": [
            "site-packages-subtree",
            "distribution-owned-prefix-files",
        ],
        "distribution_mapping": "site-packages-or-python-prefix-v1",
        "metadata_alias_policy": "deduplicate-exact-same-source-v1",
        "import_origin_overrides": dict(sorted(IMPORT_ORIGIN_OVERRIDES.items())),
        "smoke_policy": "staged-python-temp-write-strict-env-allowlist-v3",
        "smoke_check_keys": sorted(_SMOKE_CHECK_KEYS),
        "environment_passthrough_allowlist": sorted(_SMOKE_PASSTHROUGH_ENV_KEYS),
        "fixed_smoke_environment": {
            "HF_HOME": "temporary/hf",
            "HF_HUB_OFFLINE": "1",
            "MPLCONFIGDIR": "temporary/mpl",
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONNOUSERSITE": "1",
            "TEMP": "temporary",
            "TMP": "temporary",
            "TOKENIZERS_PARALLELISM": "false",
            "TORCHINDUCTOR_CACHE_DIR": "temporary/torch-inductor",
            "TRANSFORMERS_OFFLINE": "1",
            "XDG_CACHE_HOME": "temporary/xdg-cache",
        },
        "authority_policy": "capture-a-equals-capture-b-verify-both-v2",
    }


def _authority_inventory(
    authority: release.RuntimeDependencyAuthority,
) -> tuple[int, int]:
    files = (
        *authority.python.files,
        *(
            item
            for distribution in authority.distributions
            for item in distribution.files
        ),
    )
    return len(files), sum(item.bytes for item in files)


def _authority_versions(
    authority: release.RuntimeDependencyAuthority,
) -> dict[str, str]:
    return {item.name: item.version for item in authority.distributions}


def _scope_payload() -> dict[str, object]:
    return {
        "claim": "closed-python-package-prefix-byte-closure",
        "bound": [
            "cpython-prefix-regular-files",
            "dedicated-distribution-root-regular-files",
            "python-and-distribution-identities",
            "staged-smoke-observations",
        ],
        "unbound": [
            "host-os-files",
            "host-system-dlls",
            "gpu-hardware",
            "gpu-firmware",
            "cuda-driver",
            "network-state",
            "process-sandbox",
        ],
        "host_prerequisites": "observed-in-smoke-not-byte-bound",
        "network_isolation": False,
        "process_sandbox": False,
        "windows_non_delete_shared_materialization_lease": False,
        "reparse_toc_tou_residual": (
            "copy-and-smoke-use-pre-post-inventory-checks; release capture/verify "
            "leases begin only at authority capture, so pre-lease swap-back is out of scope"
        ),
    }


def _build_receipt(
    *,
    started_at_utc: str,
    completed_at_utc: str,
    staging_parent: Path,
    python: PythonSource,
    resolution: DependencyResolution,
    capture_a: StagedCapture,
    capture_b: StagedCapture,
    authority: release.RuntimeDependencyAuthority,
    source_executable_sha256: str,
) -> dict[str, object]:
    started = _parse_utc(started_at_utc, where="capture_started_at_utc")
    completed = _parse_utc(completed_at_utc, where="capture_completed_at_utc")
    if completed < started:
        raise RuntimeMaterializationError("materialization chronology is reversed")
    recipe = _recipe_payload()
    marker_environment = dict(sorted(resolution.marker_environment.items()))
    closure = [
        {
            "name": item.name,
            "version": item.version,
            "requested_extras": list(item.requested_extras),
            "requires_dist_sha256": _sha256_bytes(
                _canonical_json_bytes(list(item.requirements))
            ),
        }
        for item in resolution.distributions
    ]
    smoke_a_sha = _sha256_bytes(_canonical_json_bytes(dict(capture_a.smoke)))
    smoke_b_sha = _sha256_bytes(_canonical_json_bytes(dict(capture_b.smoke)))
    authority_files, authority_bytes = _authority_inventory(authority)
    core: dict[str, object] = {
        "schema_version": MATERIALIZATION_RECEIPT_SCHEMA_VERSION,
        "status": "materialized-two-pass-stable",
        "capture_started_at_utc": started_at_utc,
        "capture_completed_at_utc": completed_at_utc,
        "authority": {
            "relative_path": RUNTIME_AUTHORITY_RELATIVE_PATH.as_posix(),
            "schema_version": authority.schema_version,
            "authority_sha256": authority.authority_sha256,
        },
        "recipe": recipe,
        "recipe_sha256": _sha256_bytes(_canonical_json_bytes(recipe)),
        "dependency_resolution": {
            "marker_environment": marker_environment,
            "marker_environment_sha256": _sha256_bytes(
                _canonical_json_bytes(marker_environment)
            ),
            "distributions": closure,
        },
        "closure_inventory": {
            "files": authority_files,
            "bytes": authority_bytes,
        },
        "python": {
            "implementation": authority.python.implementation,
            "version": authority.python.version,
            "cache_tag": authority.python.cache_tag,
            "abi_flags": authority.python.abi_flags,
            "platform": authority.python.platform,
            "source_prefix_path_sha256": _path_identity_sha256(python.prefix),
            "source_executable_path_sha256": _path_identity_sha256(python.executable),
            "source_executable_bytes_sha256": source_executable_sha256,
            "runtime_identity_sha256": authority.python.identity_sha256,
        },
        "scope": _scope_payload(),
        "staging": {
            "path_disclosure": "sha256-only",
            "parent_path_sha256": _path_identity_sha256(staging_parent),
            "captures": [
                {
                    "capture_id": capture.capture_id,
                    "root_name": capture.root.name,
                    "absolute_path_sha256": _path_identity_sha256(capture.root),
                    "authority_sha256": authority.authority_sha256,
                    "smoke": dict(capture.smoke),
                    "smoke_record_sha256": smoke_sha,
                    "files": len(capture.snapshots),
                    "bytes": sum(item.bytes for item in capture.snapshots),
                }
                for capture, smoke_sha in (
                    (capture_a, smoke_a_sha),
                    (capture_b, smoke_b_sha),
                )
            ],
            "capture_b_copied_from_capture_a": False,
            "two_pass_byte_stable": True,
            "independent_source_provenance": False,
            "source_relationship": "same-live-install-two-discovery-copy-passes",
        },
    }
    _reject_absolute_path_leakage(core)
    return {
        **core,
        "receipt_sha256": _sha256_bytes(_canonical_json_bytes(core)),
    }


def _strict_json_object(payload: bytes, *, where: str) -> dict[str, object]:
    def reject_duplicates(pairs: list[tuple[str, object]]) -> dict[str, object]:
        result: dict[str, object] = {}
        for key, value in pairs:
            if key in result:
                raise RuntimeMaterializationError(f"duplicate JSON key in {where}: {key}")
            result[key] = value
        return result

    try:
        value = json.loads(
            payload.decode("utf-8", errors="strict"),
            object_pairs_hook=reject_duplicates,
            parse_constant=lambda constant: (_ for _ in ()).throw(
                RuntimeMaterializationError(
                    f"non-finite JSON constant in {where}: {constant}"
                )
            ),
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RuntimeMaterializationError(f"{where} is not strict JSON") from exc
    if not isinstance(value, dict) or payload != _canonical_json_bytes(value):
        raise RuntimeMaterializationError(f"{where} is not canonical JSON")
    return value


_PUBLISH_TEMP_SUFFIX = ".phase40-publish-incomplete"


def _fsync_directory(path: Path) -> None:
    """Durably publish directory-entry changes where the platform permits it."""

    # Windows durability is supplied by MoveFileExW(MOVEFILE_WRITE_THROUGH).
    # On POSIX, explicitly flush the containing directory entry as well.
    if os.name == "nt":
        return
    descriptor: int | None = None
    try:
        descriptor = os.open(path, os.O_RDONLY)
        os.fsync(descriptor)
    except OSError as exc:
        raise RuntimeMaterializationError(
            "failed to fsync fixed-output directory"
        ) from exc
    finally:
        if descriptor is not None:
            os.close(descriptor)


def _publish_temp_path(path: Path, *, nonce: str | None = None) -> Path:
    attempt = nonce if nonce is not None else secrets.token_hex(16)
    if not re.fullmatch(r"[0-9a-f]{32}", attempt):
        raise RuntimeMaterializationError("publication temp nonce is malformed")
    return path.with_name(f".{path.name}.{attempt}{_PUBLISH_TEMP_SUFFIX}")


def _ancestry_identities(
    ancestry: Sequence[Path],
) -> tuple[tuple[str, int, int], ...]:
    result: list[tuple[str, int, int]] = []
    for item in ancestry:
        observed = item.lstat()
        result.append(
            (_path_key(item), int(observed.st_dev), int(observed.st_ino))
        )
    return tuple(result)


class _PublicationParentLease:
    """Hold and revalidate the output ancestry throughout one publication.

    Windows handles omit delete sharing, preventing any held ancestor from
    being renamed or replaced while path-based MoveFileExW runs. POSIX keeps
    identity snapshots and revalidates them around promotion.
    """

    def __init__(self, parent: Path, services: _MaterializationServices) -> None:
        self.parent = Path(parent)
        self.services = services
        self._identities: tuple[tuple[str, int, int], ...] = ()
        self._handles: list[tuple[object, tuple[int, int, int]]] = []
        self._kernel32: object | None = None
        self._windows_info_type: object | None = None

    def __enter__(self) -> _PublicationParentLease:
        validated = _require_safe_existing_directory(
            self.parent,
            where="fixed-output parent",
            services=self.services,
        )
        if _path_key(validated) != _path_key(self.parent):
            raise RuntimeMaterializationError("fixed-output parent path drifted")
        ancestry = tuple(_existing_ancestry(validated))
        self._identities = _ancestry_identities(ancestry)
        try:
            if os.name == "nt":
                self._hold_windows_ancestry(ancestry)
            self.assert_intact()
            return self
        except BaseException:
            self.close()
            raise

    def _hold_windows_ancestry(self, ancestry: tuple[Path, ...]) -> None:
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
        invalid = ctypes.c_void_p(-1).value
        self._kernel32 = kernel32
        self._windows_info_type = ByHandleFileInformation
        try:
            for item, (_, _, lexical_inode) in zip(
                ancestry,
                self._identities,
                strict=True,
            ):
                handle = kernel32.CreateFileW(
                    str(item),
                    0x00000080,  # FILE_READ_ATTRIBUTES
                    0x00000001 | 0x00000002,  # share read/write; deny delete
                    None,
                    3,  # OPEN_EXISTING
                    0x00200000 | 0x02000000,  # BACKUP_SEMANTICS | OPEN_REPARSE_POINT
                    None,
                )
                if handle == invalid:
                    raise RuntimeMaterializationError(
                        "fixed-output ancestry cannot be leased: "
                        f"winerror={ctypes.get_last_error()}"
                    )
                try:
                    identity = self._inspect_windows_handle(handle)
                    handle_inode = (identity[1] << 32) | identity[2]
                    if lexical_inode and handle_inode != lexical_inode:
                        raise RuntimeMaterializationError(
                            "fixed-output ancestry changed before its lease"
                        )
                except BaseException:
                    kernel32.CloseHandle(handle)
                    raise
                self._handles.append((handle, identity))
        except BaseException:
            self.close()
            raise

    def _inspect_windows_handle(self, handle: object) -> tuple[int, int, int]:
        import ctypes

        if self._kernel32 is None or self._windows_info_type is None:
            raise RuntimeMaterializationError(
                "fixed-output ancestry handle API is unavailable"
            )
        information = self._windows_info_type()
        if not self._kernel32.GetFileInformationByHandle(
            handle, ctypes.byref(information)
        ):
            raise RuntimeMaterializationError(
                "fixed-output ancestry cannot be inspected: "
                f"winerror={ctypes.get_last_error()}"
            )
        attributes = int(information.dwFileAttributes)
        if not attributes & 0x00000010 or attributes & 0x00000400:
            raise RuntimeMaterializationError(
                "fixed-output ancestry is redirecting or not a directory"
            )
        return (
            int(information.dwVolumeSerialNumber),
            int(information.nFileIndexHigh),
            int(information.nFileIndexLow),
        )

    def assert_intact(self) -> None:
        validated = _require_safe_existing_directory(
            self.parent,
            where="fixed-output parent",
            services=self.services,
        )
        ancestry = tuple(_existing_ancestry(validated))
        identities = _ancestry_identities(ancestry)
        if identities != self._identities:
            raise RuntimeMaterializationError("fixed-output ancestry identity drifted")
        if os.name == "nt":
            if len(self._handles) != len(self._identities):
                raise RuntimeMaterializationError("fixed-output ancestry lease drifted")
            for (handle, expected_identity), (_, _, lexical_inode) in zip(
                self._handles,
                self._identities,
                strict=True,
            ):
                if self._inspect_windows_handle(handle) != expected_identity:
                    raise RuntimeMaterializationError(
                        "fixed-output held ancestry identity drifted"
                    )
                handle_inode = (expected_identity[1] << 32) | expected_identity[2]
                if lexical_inode and handle_inode != lexical_inode:
                    raise RuntimeMaterializationError(
                        "fixed-output held ancestry no longer matches its path"
                    )

    def close(self) -> None:
        if self._kernel32 is not None:
            while self._handles:
                handle, _ = self._handles.pop()
                self._kernel32.CloseHandle(handle)
        else:
            self._handles.clear()

    def __exit__(self, *_: object) -> None:
        self.close()


def _remove_owned_publish_temp(
    path: Path,
    *,
    lease: _PublicationParentLease,
) -> None:
    lease.assert_intact()
    if not (path.exists() or path.is_symlink()):
        return
    if (
        path.is_symlink()
        or not path.is_file()
        or lease.services.path_is_redirecting(path)
    ):
        raise RuntimeMaterializationError(
            f"owned fixed-output temp is not a safe regular file: {path.name}"
        )
    try:
        path.unlink()
        lease.assert_intact()
        _fsync_directory(path.parent)
    except OSError as exc:
        raise RuntimeMaterializationError(
            f"failed to clean owned fixed-output temp: {path.name}"
        ) from exc


def _write_publish_temp(path: Path, payload: bytes) -> None:
    """Write and flush a publication candidate without exposing final bytes."""

    with path.open("xb") as handle:
        remaining = memoryview(payload)
        while remaining:
            written = handle.write(remaining)
            if written is None or written <= 0:
                raise OSError("short fixed-output temp write")
            remaining = remaining[written:]
        handle.flush()
        os.fsync(handle.fileno())


def _promote_publish_temp_create_only(temporary: Path, path: Path) -> None:
    if os.name != "nt":
        os.link(temporary, path, follow_symlinks=False)
        return

    import ctypes
    from ctypes import wintypes

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.MoveFileExW.argtypes = [
        wintypes.LPCWSTR,
        wintypes.LPCWSTR,
        wintypes.DWORD,
    ]
    kernel32.MoveFileExW.restype = wintypes.BOOL
    # MOVEFILE_WRITE_THROUGH without MOVEFILE_REPLACE_EXISTING: durable and
    # create-only. A concurrent final publisher wins; it is never overwritten.
    if not kernel32.MoveFileExW(str(temporary), str(path), 0x00000008):
        code = ctypes.get_last_error()
        if code in {80, 183}:  # ERROR_FILE_EXISTS / ERROR_ALREADY_EXISTS
            raise FileExistsError(code, "fixed output already exists", str(path))
        raise OSError(code, "write-through fixed-output promotion failed", str(path))


def _write_new_or_identical(
    path: Path,
    payload: bytes,
    *,
    services: _MaterializationServices,
) -> Path:
    """Publish complete bytes atomically without ever replacing a final path.

    A unique same-directory temp means concurrent attempts never unlink one
    another. Interrupted temps are quarantined by their nonce and do not block
    later attempts. Promotion is write-through and create-only on Windows;
    POSIX uses an atomic create-only hard link plus a directory fsync.
    """

    with _PublicationParentLease(path.parent, services) as lease:
        lease.assert_intact()
        if path.exists() or path.is_symlink():
            if (
                path.is_file()
                and not services.path_is_redirecting(path)
                and path.read_bytes() == payload
            ):
                return path
            raise FileExistsError(
                f"refusing to replace drifted fixed output: {path.name}"
            )
        temporary = _publish_temp_path(path)
        try:
            _write_publish_temp(temporary, payload)
            lease.assert_intact()
            if (
                not temporary.is_file()
                or services.path_is_redirecting(temporary)
                or temporary.read_bytes() != payload
            ):
                raise RuntimeMaterializationError(
                    f"fixed-output temp verification failed: {path.name}"
                )
            try:
                _promote_publish_temp_create_only(temporary, path)
            except FileExistsError:
                if not (
                    path.is_file()
                    and not services.path_is_redirecting(path)
                    and path.read_bytes() == payload
                ):
                    raise FileExistsError(
                        f"refusing to replace drifted fixed output: {path.name}"
                    ) from None
            lease.assert_intact()
            if not (
                path.is_file()
                and not services.path_is_redirecting(path)
                and path.read_bytes() == payload
            ):
                raise RuntimeMaterializationError(
                    f"atomic fixed-output promotion verification failed: {path.name}"
                )
            _fsync_directory(path.parent)
        except (OSError, RuntimeMaterializationError) as exc:
            if isinstance(exc, FileExistsError):
                raise
            if isinstance(exc, RuntimeMaterializationError):
                raise
            raise RuntimeMaterializationError(
                f"failed to atomically publish fixed output: {path.name}"
            ) from exc
        finally:
            if temporary.exists() or temporary.is_symlink():
                _remove_owned_publish_temp(temporary, lease=lease)
    return path


def _validate_receipt(
    payload: Mapping[str, object],
    *,
    bound_authority: release.RuntimeDependencyAuthority,
) -> None:
    expected_keys = {
        "schema_version",
        "status",
        "capture_started_at_utc",
        "capture_completed_at_utc",
        "authority",
        "recipe",
        "recipe_sha256",
        "dependency_resolution",
        "closure_inventory",
        "python",
        "scope",
        "staging",
        "receipt_sha256",
    }
    if set(payload) != expected_keys:
        raise RuntimeMaterializationError("materialization receipt fields differ from schema")
    if (
        payload.get("schema_version") != MATERIALIZATION_RECEIPT_SCHEMA_VERSION
        or payload.get("status") != "materialized-two-pass-stable"
    ):
        raise RuntimeMaterializationError("materialization receipt status/schema drifted")
    started = _parse_utc(payload.get("capture_started_at_utc"), where="capture start")
    completed = _parse_utc(
        payload.get("capture_completed_at_utc"), where="capture completion"
    )
    if completed < started:
        raise RuntimeMaterializationError("materialization receipt chronology is reversed")
    receipt_sha = payload.get("receipt_sha256")
    if not isinstance(receipt_sha, str) or not _SHA256_RE.fullmatch(receipt_sha):
        raise RuntimeMaterializationError("materialization receipt hash is malformed")
    core = {key: value for key, value in payload.items() if key != "receipt_sha256"}
    if _sha256_bytes(_canonical_json_bytes(core)) != receipt_sha:
        raise RuntimeMaterializationError("materialization receipt self-hash mismatch")
    _reject_absolute_path_leakage(payload)
    recipe = payload.get("recipe")
    recipe_sha = payload.get("recipe_sha256")
    if (
        recipe != _recipe_payload()
        or not isinstance(recipe_sha, str)
        or recipe_sha != _sha256_bytes(_canonical_json_bytes(recipe))
    ):
        raise RuntimeMaterializationError("materialization staging recipe drifted")
    authority = payload.get("authority")
    if (
        not isinstance(authority, Mapping)
        or set(authority)
        != {"relative_path", "schema_version", "authority_sha256"}
        or authority.get("relative_path")
        != RUNTIME_AUTHORITY_RELATIVE_PATH.as_posix()
        or authority.get("schema_version") != release.RUNTIME_AUTHORITY_SCHEMA_VERSION
        or not isinstance(authority.get("authority_sha256"), str)
        or not _SHA256_RE.fullmatch(str(authority.get("authority_sha256")))
        or authority.get("authority_sha256") != bound_authority.authority_sha256
    ):
        raise RuntimeMaterializationError("materialization authority path drifted")
    dependency = payload.get("dependency_resolution")
    if not isinstance(dependency, Mapping) or set(dependency) != {
        "marker_environment",
        "marker_environment_sha256",
        "distributions",
    }:
        raise RuntimeMaterializationError("dependency resolution receipt is malformed")
    marker_environment = dependency.get("marker_environment")
    marker_sha = dependency.get("marker_environment_sha256")
    if (
        not isinstance(marker_environment, Mapping)
        or not marker_environment
        or not isinstance(marker_sha, str)
        or not _SHA256_RE.fullmatch(marker_sha)
        or marker_sha != _sha256_bytes(_canonical_json_bytes(marker_environment))
    ):
        raise RuntimeMaterializationError("dependency marker authority drifted")
    raw_distributions = dependency.get("distributions")
    if not isinstance(raw_distributions, list) or not raw_distributions:
        raise RuntimeMaterializationError("dependency closure receipt is malformed")
    closure_names: list[str] = []
    closure_versions: dict[str, str] = {}
    for record in raw_distributions:
        if not isinstance(record, Mapping) or set(record) != {
            "name",
            "version",
            "requested_extras",
            "requires_dist_sha256",
        }:
            raise RuntimeMaterializationError("dependency closure record is malformed")
        name = record.get("name")
        version = record.get("version")
        extras = record.get("requested_extras")
        requires_sha = record.get("requires_dist_sha256")
        if (
            not isinstance(name, str)
            or _normalize_name(name) != name
            or not isinstance(version, str)
            or _require_version(version, where=f"{name} receipt version") != version
            or not isinstance(extras, list)
            or any(not isinstance(extra, str) or not extra for extra in extras)
            or extras != sorted(set(extras))
            or not isinstance(requires_sha, str)
            or not _SHA256_RE.fullmatch(requires_sha)
        ):
            raise RuntimeMaterializationError("dependency closure record drifted")
        closure_names.append(name)
        closure_versions[name] = version
    if (
        closure_names != sorted(set(closure_names))
        or closure_versions != _authority_versions(bound_authority)
        or any(
            closure_versions.get(name) != version
            for name, version in FIXED_DIRECT_DISTRIBUTIONS.items()
        )
    ):
        raise RuntimeMaterializationError("bound dependency closure drifted")
    inventory = payload.get("closure_inventory")
    authority_files, authority_bytes = _authority_inventory(bound_authority)
    if inventory != {"files": authority_files, "bytes": authority_bytes}:
        raise RuntimeMaterializationError("bound closure inventory drifted")
    python = payload.get("python")
    if not isinstance(python, Mapping) or set(python) != {
        "implementation",
        "version",
        "cache_tag",
        "abi_flags",
        "platform",
        "source_prefix_path_sha256",
        "source_executable_path_sha256",
        "source_executable_bytes_sha256",
        "runtime_identity_sha256",
    }:
        raise RuntimeMaterializationError("Python materialization receipt is malformed")
    for key in (
        "source_prefix_path_sha256",
        "source_executable_path_sha256",
        "source_executable_bytes_sha256",
        "runtime_identity_sha256",
    ):
        if not isinstance(python.get(key), str) or not _SHA256_RE.fullmatch(
            str(python.get(key))
        ):
            raise RuntimeMaterializationError("Python materialization hash is malformed")
    expected_python_identity = {
        "implementation": bound_authority.python.implementation,
        "version": bound_authority.python.version,
        "cache_tag": bound_authority.python.cache_tag,
        "abi_flags": bound_authority.python.abi_flags,
        "platform": bound_authority.python.platform,
        "runtime_identity_sha256": bound_authority.python.identity_sha256,
    }
    if any(python.get(key) != value for key, value in expected_python_identity.items()):
        raise RuntimeMaterializationError("Python receipt differs from bound authority")
    if payload.get("scope") != _scope_payload():
        raise RuntimeMaterializationError("materialization scope claim drifted")
    staging = payload.get("staging")
    if (
        not isinstance(staging, Mapping)
        or set(staging)
        != {
            "path_disclosure",
            "parent_path_sha256",
            "captures",
            "capture_b_copied_from_capture_a",
            "two_pass_byte_stable",
            "independent_source_provenance",
            "source_relationship",
        }
        or staging.get("path_disclosure") != "sha256-only"
        or not isinstance(staging.get("parent_path_sha256"), str)
        or not _SHA256_RE.fullmatch(str(staging.get("parent_path_sha256")))
        or staging.get("capture_b_copied_from_capture_a") is not False
        or staging.get("two_pass_byte_stable") is not True
        or staging.get("independent_source_provenance") is not False
        or staging.get("source_relationship")
        != "same-live-install-two-discovery-copy-passes"
    ):
        raise RuntimeMaterializationError("materialization two-pass record drifted")
    captures = staging.get("captures")
    if not isinstance(captures, list) or [
        item.get("capture_id") if isinstance(item, Mapping) else None
        for item in captures
    ] != list(CAPTURE_ROOT_NAMES):
        raise RuntimeMaterializationError("materialization capture identities drifted")
    for expected_name, record in zip(CAPTURE_ROOT_NAMES, captures, strict=True):
        if (
            not isinstance(record, Mapping)
            or set(record)
            != {
                "capture_id",
                "root_name",
                "absolute_path_sha256",
                "authority_sha256",
                "smoke",
                "smoke_record_sha256",
                "files",
                "bytes",
            }
            or record.get("capture_id") != expected_name
            or record.get("root_name") != expected_name
            or record.get("authority_sha256") != authority.get("authority_sha256")
            or not isinstance(record.get("files"), int)
            or isinstance(record.get("files"), bool)
            or record.get("files") != authority_files
            or not isinstance(record.get("bytes"), int)
            or isinstance(record.get("bytes"), bool)
            or record.get("bytes") != authority_bytes
        ):
            raise RuntimeMaterializationError("materialization capture record drifted")
        for key in ("absolute_path_sha256", "smoke_record_sha256"):
            if not isinstance(record.get(key), str) or not _SHA256_RE.fullmatch(
                str(record.get(key))
            ):
                raise RuntimeMaterializationError(
                    "materialization capture hash is malformed"
                )
        smoke = record.get("smoke")
        if not isinstance(smoke, Mapping):
            raise RuntimeMaterializationError("materialization smoke record is missing")
        _validate_smoke_result(
            smoke,
            expected_versions=closure_versions,
            expected_python_version=bound_authority.python.version,
        )
        if record.get("smoke_record_sha256") != _sha256_bytes(
            _canonical_json_bytes(smoke)
        ):
            raise RuntimeMaterializationError("materialization smoke hash drifted")


def _build_completion_marker(
    *,
    authority: release.RuntimeDependencyAuthority,
    receipt: Mapping[str, object],
) -> dict[str, object]:
    receipt_sha = receipt.get("receipt_sha256")
    if not isinstance(receipt_sha, str) or not _SHA256_RE.fullmatch(receipt_sha):
        raise RuntimeMaterializationError("completion marker receipt hash is malformed")
    core: dict[str, object] = {
        "schema_version": MATERIALIZATION_COMPLETE_SCHEMA_VERSION,
        "status": "complete",
        "authority_relative_path": RUNTIME_AUTHORITY_RELATIVE_PATH.as_posix(),
        "authority_sha256": authority.authority_sha256,
        "receipt_relative_path": MATERIALIZATION_RECEIPT_RELATIVE_PATH.as_posix(),
        "receipt_sha256": receipt_sha,
    }
    return {
        **core,
        "completion_sha256": _sha256_bytes(_canonical_json_bytes(core)),
    }


def _validate_completion_marker(
    marker: Mapping[str, object],
    *,
    authority: release.RuntimeDependencyAuthority,
    receipt: Mapping[str, object],
) -> None:
    expected = _build_completion_marker(authority=authority, receipt=receipt)
    if marker != expected:
        raise RuntimeMaterializationError("materialization completion marker drifted")
    _reject_absolute_path_leakage(marker, where="materialization completion marker")


def _load_fixed_json(
    repository: Path,
    relative_path: PurePosixPath,
    *,
    description: str,
) -> dict[str, object]:
    path = repository / relative_path
    if (
        not _is_within(path, repository)
        or not path.is_file()
        or any(
            _default_path_is_redirecting(component)
            for component in _existing_ancestry(path)
        )
    ):
        raise RuntimeMaterializationError(f"fixed {description} is unavailable")
    return _strict_json_object(path.read_bytes(), where=description)


def _load_receipt_authority(
    *,
    repository: Path,
    require_completion: bool,
) -> tuple[
    dict[str, object],
    release.RuntimeDependencyAuthority,
    dict[str, object] | None,
]:
    marker = (
        _load_fixed_json(
            repository,
            MATERIALIZATION_COMPLETE_RELATIVE_PATH,
            description="materialization completion marker",
        )
        if require_completion
        else None
    )
    authority = release.load_runtime_dependency_authority(
        repository / RUNTIME_AUTHORITY_RELATIVE_PATH
    )
    receipt = _load_fixed_json(
        repository,
        MATERIALIZATION_RECEIPT_RELATIVE_PATH,
        description="materialization receipt",
    )
    _validate_receipt(receipt, bound_authority=authority)
    if marker is not None:
        _validate_completion_marker(marker, authority=authority, receipt=receipt)
    return receipt, authority, marker


def load_runtime_materialization_receipt(*, repo_root: Path) -> dict[str, object]:
    """Load fixed canonical bytes only after the marker-last transaction completes."""

    repository = _absolute_input(repo_root, where="repository root")
    if not repository.is_dir() or any(
        _default_path_is_redirecting(component)
        for component in _existing_ancestry(repository)
    ):
        raise RuntimeMaterializationError("repository root is missing or redirecting")
    payload, _, _ = _load_receipt_authority(
        repository=repository,
        require_completion=True,
    )
    return payload


def _default_services() -> _MaterializationServices:
    return _MaterializationServices(
        metadata=_default_metadata_hooks(),
        discover_python=_discover_live_python,
        path_is_redirecting=_default_path_is_redirecting,
        smoke_runner=_run_staged_smoke,
        now=lambda: datetime.now(timezone.utc),
        capture_authority=release.capture_runtime_dependency_authority,
        verify_authority=release.verify_runtime_dependency_authority,
        publication_hook=lambda _: None,
    )


def _validated_python_source(
    *,
    services: _MaterializationServices,
    staging_parent: Path,
) -> tuple[PythonSource, str]:
    observed = services.discover_python()
    python_prefix = _require_safe_existing_directory(
        observed.prefix,
        where="Python prefix",
        services=services,
    )
    site_packages = _require_safe_existing_directory(
        observed.site_packages,
        where="Python site-packages",
        services=services,
    )
    executable = _require_safe_regular_file(
        observed.executable,
        where="Python executable",
        services=services,
    )
    if not _is_within(site_packages, python_prefix) or not _is_within(
        executable, python_prefix
    ):
        raise RuntimeMaterializationError(
            "Python executable/site-packages must be inside the captured prefix"
        )
    _require_disjoint(python_prefix, staging_parent, where="Python/staging")
    normalized = PythonSource(
        implementation=observed.implementation,
        version=observed.version,
        cache_tag=observed.cache_tag,
        abi_flags=observed.abi_flags,
        platform=observed.platform,
        prefix=python_prefix,
        site_packages=site_packages,
        executable=executable,
    )
    executable_bytes, executable_sha = _hash_regular_file(
        executable,
        services=services,
        where="source Python executable",
    )
    if executable_bytes <= 0:
        raise RuntimeMaterializationError("source Python executable is empty")
    return normalized, executable_sha


def _python_source_identity(source: PythonSource) -> dict[str, str]:
    return {
        "implementation": source.implementation,
        "version": source.version,
        "cache_tag": source.cache_tag,
        "abi_flags": source.abi_flags,
        "platform": source.platform,
        "prefix_path_sha256": _path_identity_sha256(source.prefix),
        "site_packages_path_sha256": _path_identity_sha256(source.site_packages),
        "executable_path_sha256": _path_identity_sha256(source.executable),
    }


def _resolution_identity(resolution: DependencyResolution) -> bytes:
    return _canonical_json_bytes(
        {
            "marker_environment": dict(resolution.marker_environment),
            "distributions": [
                {
                    "name": item.name,
                    "version": item.version,
                    "requirements": list(item.requirements),
                    "requested_extras": list(item.requested_extras),
                }
                for item in resolution.distributions
            ],
        }
    )


def _capture_from_authority(
    *,
    capture_id: str,
    root: Path,
    authority: release.RuntimeDependencyAuthority,
    smoke: Mapping[str, object],
) -> StagedCapture:
    snapshots = [
        FileSnapshot(
            relative_path=(
                PurePosixPath(PYTHON_RUNTIME_ROOT_NAME) / item.relative_path
            ).as_posix(),
            bytes=item.bytes,
            sha256=item.sha256,
        )
        for item in authority.python.files
    ]
    distributions: list[release.DistributionCaptureInput] = []
    for item in authority.distributions:
        install_root = root / DISTRIBUTIONS_ROOT_NAME / item.name
        distributions.append(
            release.DistributionCaptureInput(
                name=item.name,
                version=item.version,
                install_root=install_root,
                import_origin=Path(item.import_origin),
                declared_files=tuple(Path(file.relative_path) for file in item.files),
            )
        )
        snapshots.extend(
            FileSnapshot(
                relative_path=(
                    PurePosixPath(DISTRIBUTIONS_ROOT_NAME)
                    / item.name
                    / file.relative_path
                ).as_posix(),
                bytes=file.bytes,
                sha256=file.sha256,
            )
            for file in item.files
        )
    return StagedCapture(
        capture_id=capture_id,
        root=root,
        python=release.PythonCaptureInput(
            implementation=authority.python.implementation,
            version=authority.python.version,
            cache_tag=authority.python.cache_tag,
            abi_flags=authority.python.abi_flags,
            platform=authority.python.platform,
            executable_root=root / PYTHON_RUNTIME_ROOT_NAME,
            executable=Path(authority.python.executable.relative_path),
        ),
        distributions=tuple(distributions),
        snapshots=tuple(sorted(snapshots, key=lambda item: item.relative_path)),
        smoke=MappingProxyType(dict(smoke)),
    )


def _receipt_capture_smokes(
    receipt: Mapping[str, object],
) -> dict[str, Mapping[str, object]]:
    staging = receipt.get("staging")
    if not isinstance(staging, Mapping) or not isinstance(staging.get("captures"), list):
        raise RuntimeMaterializationError("receipt capture records are unavailable")
    result: dict[str, Mapping[str, object]] = {}
    for record in staging["captures"]:
        if not isinstance(record, Mapping):
            raise RuntimeMaterializationError("receipt capture record is malformed")
        capture_id = record.get("capture_id")
        smoke = record.get("smoke")
        if not isinstance(capture_id, str) or not isinstance(smoke, Mapping):
            raise RuntimeMaterializationError("receipt capture smoke is malformed")
        result[capture_id] = smoke
    if tuple(result) != CAPTURE_ROOT_NAMES:
        raise RuntimeMaterializationError("receipt capture order drifted")
    return result


def _publish_materialization(
    *,
    repository: Path,
    authority: release.RuntimeDependencyAuthority,
    receipt: Mapping[str, object],
    services: _MaterializationServices,
) -> tuple[dict[str, object], Path]:
    """Publish replay-safe fixed bytes with the completion marker strictly last."""

    authority_path = repository / RUNTIME_AUTHORITY_RELATIVE_PATH
    receipt_path = repository / MATERIALIZATION_RECEIPT_RELATIVE_PATH
    completion_path = repository / MATERIALIZATION_COMPLETE_RELATIVE_PATH
    _write_new_or_identical(
        authority_path,
        release.canonical_json_bytes(authority.as_dict()),
        services=services,
    )
    services.publication_hook("authority-published")
    _write_new_or_identical(
        receipt_path,
        _canonical_json_bytes(dict(receipt)),
        services=services,
    )
    services.publication_hook("receipt-published")
    completion = _build_completion_marker(authority=authority, receipt=receipt)
    _write_new_or_identical(
        completion_path,
        _canonical_json_bytes(completion),
        services=services,
    )
    services.publication_hook("completion-published")
    return completion, completion_path


def _verify_runtime_dependency_materialization(
    *,
    repo_root: Path,
    staging_parent: Path,
    services: _MaterializationServices,
    require_completion: bool = True,
) -> MaterializationResult:
    repository = _require_safe_existing_directory(
        repo_root,
        where="repository root",
        services=services,
    )
    staging = _require_safe_existing_directory(
        staging_parent,
        where="external staging parent",
        services=services,
    )
    _require_disjoint(repository, staging, where="repository/staging")
    receipt, authority, completion = _load_receipt_authority(
        repository=repository,
        require_completion=require_completion,
    )
    smokes = _receipt_capture_smokes(receipt)
    expected = _authority_versions(authority)
    source_python = services.discover_python()
    captures = tuple(
        _capture_from_authority(
            capture_id=name,
            root=_require_safe_existing_directory(
                staging / name,
                where=f"fixed staging child {name}",
                services=services,
            ),
            authority=authority,
            smoke=smokes[name],
        )
        for name in CAPTURE_ROOT_NAMES
    )
    for capture in captures:
        _verify_stage_snapshot(capture, services=services)
        services.verify_authority(
            authority,
            capture.python,
            capture.distributions,
            expected_distributions=expected,
        )
        observed = dict(services.smoke_runner(capture, expected, source_python))
        _validate_smoke_result(
            observed,
            expected_versions=expected,
            expected_python_version=authority.python.version,
        )
        if observed != dict(capture.smoke):
            raise RuntimeMaterializationError(
                f"{capture.capture_id} staged smoke replay drifted"
            )
        _verify_stage_snapshot(capture, services=services)
    _verify_stage_snapshot(captures[0], services=services)
    if completion is None:
        completion = _build_completion_marker(authority=authority, receipt=receipt)
    return MaterializationResult(
        authority=authority,
        authority_path=repository / RUNTIME_AUTHORITY_RELATIVE_PATH,
        receipt=MappingProxyType(dict(receipt)),
        receipt_path=repository / MATERIALIZATION_RECEIPT_RELATIVE_PATH,
        completion=MappingProxyType(dict(completion)),
        completion_path=repository / MATERIALIZATION_COMPLETE_RELATIVE_PATH,
    )


def verify_runtime_dependency_materialization(
    *,
    repo_root: Path,
    staging_parent: Path,
) -> MaterializationResult:
    """Re-hash both fixed trees and replay both exact staged-runtime smokes."""

    return _verify_runtime_dependency_materialization(
        repo_root=repo_root,
        staging_parent=staging_parent,
        services=_default_services(),
    )


def _materialize_runtime_dependency_authority(
    *,
    repo_root: Path,
    staging_parent: Path,
    services: _MaterializationServices,
) -> MaterializationResult:
    """Private injectable core; production entry points always use fixed services."""

    active = services
    repository = _require_safe_existing_directory(
        repo_root,
        where="repository root",
        services=active,
    )
    staging = _require_safe_existing_directory(
        staging_parent,
        where="external staging parent",
        services=active,
    )
    _require_disjoint(repository, staging, where="repository/staging")
    authority_path = repository / RUNTIME_AUTHORITY_RELATIVE_PATH
    receipt_path = repository / MATERIALIZATION_RECEIPT_RELATIVE_PATH
    completion_path = repository / MATERIALIZATION_COMPLETE_RELATIVE_PATH
    output_parent = _require_safe_existing_directory(
        authority_path.parent,
        where="fixed Phase 40 model directory",
        services=active,
    )
    if not all(
        _path_key(output_parent) == _path_key(path.parent)
        for path in (receipt_path, completion_path)
    ):
        raise RuntimeMaterializationError("fixed runtime outputs do not share one parent")
    if completion_path.exists() or completion_path.is_symlink():
        return _verify_runtime_dependency_materialization(
            repo_root=repository,
            staging_parent=staging,
            services=active,
        )
    authority_exists = authority_path.exists() or authority_path.is_symlink()
    receipt_exists = receipt_path.exists() or receipt_path.is_symlink()
    capture_children_exist = tuple(
        (staging / name).exists() or (staging / name).is_symlink()
        for name in CAPTURE_ROOT_NAMES
    )
    if receipt_exists and not authority_exists:
        raise RuntimeMaterializationError(
            "partial publication has a receipt without its bound authority"
        )
    if authority_exists:
        if not all(capture_children_exist):
            raise RuntimeMaterializationError(
                "partial publication cannot recover without both fixed capture trees"
            )
        if receipt_exists:
            verified = _verify_runtime_dependency_materialization(
                repo_root=repository,
                staging_parent=staging,
                services=active,
                require_completion=False,
            )
            completion, _ = _publish_materialization(
                repository=repository,
                authority=verified.authority,
                receipt=verified.receipt,
                services=active,
            )
            loaded = load_runtime_materialization_receipt(repo_root=repository)
            if loaded != dict(verified.receipt):
                raise RuntimeMaterializationError(
                    "recovered materialization receipt replay drifted"
                )
            return MaterializationResult(
                authority=verified.authority,
                authority_path=authority_path,
                receipt=verified.receipt,
                receipt_path=receipt_path,
                completion=MappingProxyType(dict(completion)),
                completion_path=completion_path,
            )
        raise RuntimeMaterializationError(
            "authority-only partial publication cannot prove original two-pass "
            "provenance; refusing receipt recovery"
        )
    if receipt_exists or any(capture_children_exist):
        raise FileExistsError(
            "incomplete pre-authority capture exists; refusing destructive recovery"
        )
    for name in CAPTURE_ROOT_NAMES:
        if not _SAFE_ROOT_NAME_RE.fullmatch(name):
            raise RuntimeMaterializationError("fixed capture child name is unsafe")
        child = staging / name

    started_at = _utc_text(active.now())
    python_a, source_executable_sha = _validated_python_source(
        services=active,
        staging_parent=staging,
    )
    _require_disjoint(python_a.prefix, repository, where="Python/repository")
    resolution_a = resolve_dependency_closure(metadata=active.metadata)
    prepared_a = prepare_distribution_sources(
        resolution_a,
        python_a,
        metadata=active.metadata,
        services=active,
    )
    expected = resolution_a.expected_versions
    capture_a = _stage_one_capture(
        capture_id=CAPTURE_ROOT_NAMES[0],
        root=staging / CAPTURE_ROOT_NAMES[0],
        python=python_a,
        distributions=prepared_a,
        expected_versions=expected,
        services=active,
    )

    # Re-discover every live input for B.  Reusing A's prepared manifest would
    # miss a concurrent RECORD/member or import-origin change even though the
    # bytes were copied from the live prefix again.
    python_b, source_executable_sha_b = _validated_python_source(
        services=active,
        staging_parent=staging,
    )
    _require_disjoint(python_b.prefix, repository, where="Python/repository")
    if (
        _python_source_identity(python_a) != _python_source_identity(python_b)
        or source_executable_sha_b != source_executable_sha
    ):
        raise RuntimeMaterializationError("live Python identity drifted between A and B")
    resolution_b = resolve_dependency_closure(metadata=active.metadata)
    if _resolution_identity(resolution_a) != _resolution_identity(resolution_b):
        raise RuntimeMaterializationError(
            "live dependency resolution drifted between A and B"
        )
    prepared_b = prepare_distribution_sources(
        resolution_b,
        python_b,
        metadata=active.metadata,
        services=active,
    )
    capture_b = _stage_one_capture(
        capture_id=CAPTURE_ROOT_NAMES[1],
        root=staging / CAPTURE_ROOT_NAMES[1],
        python=python_b,
        distributions=prepared_b,
        expected_versions=expected,
        services=active,
    )
    # The B smoke runs beside A.  Recheck both roots so even a hostile runtime
    # that reaches across its own capture root cannot alter either authority.
    _verify_stage_snapshot(capture_a, services=active)
    _verify_stage_snapshot(capture_b, services=active)
    authority_a = active.capture_authority(
        capture_a.python,
        capture_a.distributions,
        expected_distributions=expected,
    )
    authority_b = active.capture_authority(
        capture_b.python,
        capture_b.distributions,
        expected_distributions=expected,
    )
    if release.canonical_json_bytes(authority_a.as_dict()) != release.canonical_json_bytes(
        authority_b.as_dict()
    ):
        raise RuntimeMaterializationError(
            "two-pass A/B runtime authorities are not byte-identical"
        )
    active.verify_authority(
        authority_a,
        capture_a.python,
        capture_a.distributions,
        expected_distributions=expected,
    )
    active.verify_authority(
        authority_a,
        capture_b.python,
        capture_b.distributions,
        expected_distributions=expected,
    )
    completed_at = _utc_text(active.now())
    receipt = _build_receipt(
        started_at_utc=started_at,
        completed_at_utc=completed_at,
        staging_parent=staging,
        python=python_a,
        resolution=resolution_a,
        capture_a=capture_a,
        capture_b=capture_b,
        authority=authority_a,
        source_executable_sha256=source_executable_sha,
    )
    _validate_receipt(receipt, bound_authority=authority_a)
    completion, _ = _publish_materialization(
        repository=repository,
        authority=authority_a,
        receipt=receipt,
        services=active,
    )
    loaded = load_runtime_materialization_receipt(repo_root=repository)
    if loaded != receipt:
        raise RuntimeMaterializationError("fixed materialization receipt replay drifted")
    return MaterializationResult(
        authority=authority_a,
        authority_path=authority_path,
        receipt=MappingProxyType(dict(receipt)),
        receipt_path=receipt_path,
        completion=MappingProxyType(dict(completion)),
        completion_path=completion_path,
    )


def materialize_runtime_dependency_authority(
    *,
    repo_root: Path,
    staging_parent: Path,
) -> MaterializationResult:
    """Materialize with the fixed production metadata, smoke, and writers only."""

    return _materialize_runtime_dependency_authority(
        repo_root=repo_root,
        staging_parent=staging_parent,
        services=_default_services(),
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m src.model_adaptation.phase40_runtime_materialize",
        description=(
            "Materialize the fixed Phase 40 closed Python package/prefix byte "
            "authority from two external capture passes."
        ),
        allow_abbrev=False,
    )
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--staging-parent", type=Path, required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    result = materialize_runtime_dependency_authority(
        repo_root=args.repo_root,
        staging_parent=args.staging_parent,
    )
    summary = {
        "status": "materialized",
        "authority_relative_path": RUNTIME_AUTHORITY_RELATIVE_PATH.as_posix(),
        "authority_sha256": result.authority.authority_sha256,
        "receipt_relative_path": MATERIALIZATION_RECEIPT_RELATIVE_PATH.as_posix(),
        "receipt_sha256": result.receipt["receipt_sha256"],
        "completion_relative_path": MATERIALIZATION_COMPLETE_RELATIVE_PATH.as_posix(),
        "completion_sha256": result.completion["completion_sha256"],
    }
    sys.stdout.buffer.write(_canonical_json_bytes(summary))
    return 0


if __name__ == "__main__":  # pragma: no cover - exercised through main()
    raise SystemExit(main())


__all__ = [
    "CAPTURE_ROOT_NAMES",
    "DependencyResolution",
    "FIXED_DIRECT_DISTRIBUTIONS",
    "IMPORT_ORIGIN_OVERRIDES",
    "MATERIALIZATION_COMPLETE_RELATIVE_PATH",
    "MATERIALIZATION_COMPLETE_SCHEMA_VERSION",
    "MATERIALIZATION_RECEIPT_RELATIVE_PATH",
    "MATERIALIZATION_RECEIPT_SCHEMA_VERSION",
    "MaterializationResult",
    "MetadataHooks",
    "PythonSource",
    "RUNTIME_AUTHORITY_RELATIVE_PATH",
    "RuntimeMaterializationError",
    "build_parser",
    "load_runtime_materialization_receipt",
    "main",
    "materialize_runtime_dependency_authority",
    "prepare_distribution_sources",
    "resolve_dependency_closure",
    "verify_runtime_dependency_materialization",
]
