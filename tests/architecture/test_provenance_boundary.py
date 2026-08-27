"""Provenance and held-out-data boundary tests for Phase 41.1 Plan 01."""

from __future__ import annotations

from dataclasses import replace
import hashlib
import json
import ntpath
import os
from pathlib import Path, PurePosixPath
import subprocess
import sys
from typing import Any

import pytest

from scripts import archive_phase41_source_closure as archive


REPO_ROOT = Path(__file__).parents[2]
FIXTURE_PATH = Path(__file__).parent / "fixtures" / "protected_authority_baseline.json"
GUARD_CONTRACT_PATH = Path(__file__).parent / "fixtures" / "phase411_guard_contract.json"


def _resolve_fixed_symbol(name: str) -> object | None:
    parts = name.split(".")
    try:
        owner: object = __import__(parts[0])
    except ImportError:
        return None
    for index, part in enumerate(parts[1:], start=1):
        value = getattr(owner, part, None)
        if value is None:
            try:
                value = __import__(".".join(parts[: index + 1]), fromlist=[part])
            except ImportError:
                return None
        owner = value
    return owner


def _guard_contract() -> dict[str, Any]:
    contract = _strict_json(GUARD_CONTRACT_PATH.read_bytes())
    assert list(contract) == [
        "boundary", "native_process_symbols", "process_symbols",
        "protected_roots", "schema_version",
    ]
    assert contract["schema_version"] == "phase411-guard-contract-v2"
    assert contract["boundary"] == "requires-external-os-process-isolation"
    assert len(contract["protected_roots"]) == len(set(contract["protected_roots"])) == 7
    assert len(contract["process_symbols"]) == len(set(contract["process_symbols"])) == 53
    assert len(contract["native_process_symbols"]) == len(
        set(contract["native_process_symbols"])
    ) == 9
    return contract


def _manifest_root(spec: str) -> str:
    if spec.startswith("repo:"):
        value = ntpath.join(
            os.fspath(REPO_ROOT), spec.removeprefix("repo:").replace("/", "\\")
        )
    else:
        value = spec
    return ntpath.normcase(ntpath.normpath(value))


def test_guard_origin_and_contract_are_exact_before_collection() -> None:
    import sitecustomize

    contract = _guard_contract()
    expected_origin = ntpath.normcase(
        ntpath.normpath(os.fspath(Path(__file__).parent / "bootstrap" / "sitecustomize.py"))
    )
    assert ntpath.normcase(ntpath.normpath(sitecustomize.__file__)) == expected_origin
    assert ntpath.normcase(ntpath.normpath(sitecustomize.__spec__.origin)) == expected_origin
    expected_roots = tuple(_manifest_root(item) for item in contract["protected_roots"])
    assert sitecustomize.PHASE411_GUARD_POLICY_VERSION == "phase411-guard-v2"
    assert sitecustomize.PHASE411_PROCESS_POLICY == "python-defense-in-depth"
    assert sitecustomize.PHASE411_GUARD_BOUNDARY == contract["boundary"]
    assert sitecustomize.PHASE411_PREINSTALL_DESCRIPTOR_PROBES == 0
    assert sitecustomize.PHASE411_PROTECTED_ROOTS == expected_roots
    assert tuple(sitecustomize.PHASE411_PROCESS_OPERATION_DISPOSITIONS) == tuple(
        contract["process_symbols"]
    )
    assert set(sitecustomize.PHASE411_PROCESS_OPERATION_DISPOSITIONS.values()) <= {
        "wrapped", "unavailable_on_platform"
    }
    assert sitecustomize.PHASE411_INSTALLED_PROCESS_OPERATIONS == tuple(
        name for name in contract["process_symbols"]
        if sitecustomize.PHASE411_PROCESS_OPERATION_DISPOSITIONS[name] == "wrapped"
    )
    assert sitecustomize.PHASE411_INSTALLED_PATH_OPERATIONS
    assert sitecustomize.PHASE411_INSTALLED_DESCRIPTOR_OPERATIONS
    assert not hasattr(sitecustomize, "_ORIGINALS")

    def resolve_guarded(name: str) -> object | None:
        if name.startswith("Path."):
            return getattr(Path, name.split(".", 1)[1], None)
        return _resolve_fixed_symbol(name)

    guarded_names = (
        *sitecustomize.PHASE411_INSTALLED_PATH_OPERATIONS,
        *sitecustomize.PHASE411_INSTALLED_DESCRIPTOR_OPERATIONS,
        *sitecustomize.PHASE411_INSTALLED_PROCESS_OPERATIONS,
    )
    for name in guarded_names:
        wrapper = resolve_guarded(name)
        assert callable(wrapper), name
        assert not hasattr(wrapper, "__wrapped__"), name
        assert not hasattr(wrapper, "__phase411_original__"), name
        assert not any(callable(value) for value in (getattr(wrapper, "__defaults__", None) or ())), name
        assert not any(
            callable(value)
            for value in (getattr(wrapper, "__kwdefaults__", None) or {}).values()
        ), name


def test_guard_blocks_all_exact_authority_roots_and_alias_spellings() -> None:
    import sitecustomize

    for root in sitecustomize.PHASE411_PROTECTED_ROOTS:
        aliases = (
            root,
            root + "\\synthetic-never-opened.bin",
            root + ":synthetic-stream",
            "\\\\?\\" + root,
            root.replace("\\", "/").swapcase(),
            ntpath.join(root, "synthetic", "..", "never-opened.bin"),
        )
        for alias in aliases:
            with pytest.raises(PermissionError, match="forbidden authority path"):
                os.stat(alias)
    assert sitecustomize.phase411_guard_snapshot()["underlying_forbidden"] == []


def test_guard_path_operation_inventory_rejects_before_underlying_calls() -> None:
    import sitecustomize

    calls = {"original": 0}

    def original(*_args: object, **_kwargs: object) -> None:
        calls["original"] += 1

    guarded = sitecustomize._make_path_guard("synthetic.open", original)
    with pytest.raises(PermissionError, match="forbidden authority path"):
        guarded(sitecustomize.PHASE411_PROTECTED_ROOTS[0] + "\\never-opened")
    assert calls == {"original": 0}
    for name in sitecustomize.PHASE411_INSTALLED_PATH_OPERATIONS:
        assert isinstance(name, str) and "." in name


def test_guard_descriptor_operation_inventory_rejects_before_underlying_calls() -> None:
    import sitecustomize

    calls = {"original": 0}

    def original(*_args: object, **_kwargs: object) -> None:
        calls["original"] += 1

    guarded = sitecustomize._make_descriptor_consumer(
        "synthetic.fstat", original, keywords=("fd",)
    )
    for call in (lambda: guarded(object()), lambda: guarded(fd=object())):
        with pytest.raises(PermissionError, match="descriptor capability denied"):
            call()
    assert calls == {"original": 0}
    required = {
        "os.fstat", "os.fchmod", "os.ftruncate", "os.fsync", "os.read",
        "os.write", "os.lseek", "os.dup", "os.dup2",
    }
    assert required <= set(sitecustomize.PHASE411_INSTALLED_DESCRIPTOR_OPERATIONS)

    unknown = max(sitecustomize.phase411_descriptor_capabilities(), default=100) + 10000
    signatures = {
        "fdopen": ((unknown, "rb"), {"fd": unknown, "mode": "rb"}),
        "fstat": ((unknown,), {"fd": unknown}),
        "fchmod": ((unknown, 0o600), {"fd": unknown, "mode": 0o600}),
        "ftruncate": ((unknown, 0), {"fd": unknown, "length": 0}),
        "fsync": ((unknown,), {"fd": unknown}),
        "read": ((unknown, 1), {"fd": unknown, "length": 1}),
        "write": ((unknown, b""), {"fd": unknown, "data": b""}),
        "lseek": ((unknown, 0, os.SEEK_SET), {"fd": unknown, "position": 0, "how": os.SEEK_SET}),
        "fchdir": ((unknown,), {"fd": unknown}),
        "pread": ((unknown, 1, 0), {"fd": unknown, "length": 1, "offset": 0}),
        "readv": ((unknown, [bytearray(1)]), {"fd": unknown, "buffers": [bytearray(1)]}),
        "preadv": ((unknown, [bytearray(1)], 0), {"fd": unknown, "buffers": [bytearray(1)], "offset": 0}),
    }
    for attribute, (positional, keyword) in signatures.items():
        operation = getattr(os, attribute, None)
        if operation is None:
            continue
        for args, kwargs in ((positional, {}), ((), keyword)):
            with pytest.raises(PermissionError, match="descriptor capability denied"):
                operation(*args, **kwargs)
    descriptor_mutations = [
        lambda: os.close(unknown),
        lambda: os.close(fd=unknown),
        lambda: open(unknown, "rb"),
        lambda: open(file=unknown, mode="rb"),
    ]
    if hasattr(os, "dup"):
        descriptor_mutations.extend((lambda: os.dup(unknown), lambda: os.dup(fd=unknown)))
    if hasattr(os, "dup2"):
        descriptor_mutations.extend(
            (
                lambda: os.dup2(unknown, unknown + 1),
                lambda: os.dup2(fd=unknown, fd2=unknown + 1),
            )
        )
    for attempt in descriptor_mutations:
        with pytest.raises(PermissionError, match="descriptor capability denied"):
            attempt()


def test_guard_process_operation_inventory_rejects_before_underlying_calls() -> None:
    import sitecustomize

    contract = _guard_contract()
    calls = {"coercion": 0, "underlying": 0}

    class Trap:
        def __fspath__(self) -> str:
            calls["coercion"] += 1
            return "never"

        def __str__(self) -> str:
            calls["coercion"] += 1
            return "never"

    synthetic = sitecustomize._make_process_deny_wrapper("synthetic.process")
    with pytest.raises(PermissionError, match="process execution denied"):
        synthetic(Trap())
    assert calls == {"coercion": 0, "underlying": 0}

    resolved = {name: _resolve_fixed_symbol(name) for name in contract["process_symbols"]}
    expected = {
        name: ("wrapped" if value is not None else "unavailable_on_platform")
        for name, value in resolved.items()
    }
    assert dict(sitecustomize.PHASE411_PROCESS_OPERATION_DISPOSITIONS) == expected
    for name, value in resolved.items():
        if value is None:
            continue
        assert getattr(value, "__phase411_process_guard__", None) == name
        with pytest.raises(PermissionError, match="process execution denied"):
            value(Trap())
    assert calls == {"coercion": 0, "underlying": 0}

    independent_native_symbols = (
        "nt.system", "posix.system", "ctypes.CDLL.__init__",
        "ctypes.PyDLL.__init__", "ctypes.WinDLL.__init__",
        "ctypes.OleDLL.__init__", "ctypes._dlopen", "_ctypes.dlopen",
        "importlib.reload",
    )
    assert tuple(contract["native_process_symbols"]) == independent_native_symbols
    assert tuple(sitecustomize.PHASE411_NATIVE_PROCESS_OPERATION_DISPOSITIONS) == (
        independent_native_symbols
    )
    native_resolved = {
        name: _resolve_fixed_symbol(name) for name in independent_native_symbols
    }
    external_native_symbols = {
        "ctypes.CDLL.__init__", "ctypes.PyDLL.__init__",
        "ctypes.WinDLL.__init__", "ctypes.OleDLL.__init__",
        "ctypes._dlopen", "_ctypes.dlopen",
    }
    expected_native = {
        name: (
            "unavailable_on_platform"
            if value is None
            else "external_os_isolation_required"
            if name in external_native_symbols
            else "wrapped"
        )
        for name, value in native_resolved.items()
    }
    assert dict(sitecustomize.PHASE411_NATIVE_PROCESS_OPERATION_DISPOSITIONS) == expected_native
    for name, value in native_resolved.items():
        if value is None:
            continue
        if name in external_native_symbols:
            assert not hasattr(value, "__phase411_process_guard__")
            continue
        assert getattr(value, "__phase411_process_guard__", None) == name
        with pytest.raises(PermissionError, match="process execution denied"):
            value(Trap())
    assert calls == {"coercion": 0, "underlying": 0}


def test_guard_descriptor_capabilities_are_post_install_only(
    tmp_path: Path,
    phase411_windows_bound_descriptors: list[int],
) -> None:
    import sitecustomize

    assert sitecustomize.PHASE411_PREINSTALL_DESCRIPTOR_PROBES == 0
    unknown = max(sitecustomize.phase411_descriptor_capabilities(), default=100) + 10000
    with pytest.raises(PermissionError, match="descriptor capability denied"):
        os.fstat(unknown)
    safe = tmp_path / "post-install-capability.txt"
    descriptor = os.open(safe, os.O_CREAT | os.O_RDWR)
    try:
        assert descriptor in sitecustomize.phase411_descriptor_capabilities()
        assert os.fstat(descriptor).st_size == 0
    finally:
        os.close(descriptor)
    assert descriptor not in sitecustomize.phase411_descriptor_capabilities()
    read_fd, write_fd = os.pipe()
    try:
        assert {read_fd, write_fd} <= set(sitecustomize.phase411_descriptor_capabilities())
    finally:
        os.close(read_fd)
        os.close(write_fd)
    if os.name == "nt":
        layout = _synthetic_layout(tmp_path / "windows-bound-parent")
        archive._archive_bound_source_closure_for_test(layout)
        assert phase411_windows_bound_descriptors
        removals = set(sitecustomize.phase411_guard_snapshot()["descriptor_removals"])
        assert set(phase411_windows_bound_descriptors) <= removals


def test_protected_authority_fixture_is_strict_and_complete() -> None:
    baseline = _strict_json(FIXTURE_PATH.read_bytes())
    assert list(baseline) == [
        "archive_publication_commit", "baseline_commit", "expected_member_count",
        "historical_mirror", "protected_authorities", "receipt_bytes", "schema_version",
    ]
    assert baseline["archive_publication_commit"] == "b0d24820720f53100d9a94174790d70b5354fa27"
    assert baseline["expected_member_count"] == 40
    assert baseline["receipt_bytes"] == 1746
    assert baseline["schema_version"] == "phase411-protected-authority-baseline-v1"
    mirror = baseline["historical_mirror"]
    assert list(mirror) == [
        "destination", "launcher", "manifest_schema_version", "source_tree_sha256", "sources"
    ]
    assert len(mirror["sources"]) == 37
    assert all(list(item) == ["bytes", "path", "sha256"] for item in mirror["sources"])
    assert list(mirror["launcher"]) == ["bytes", "path", "sha256"]
    assert len(baseline["protected_authorities"]) == 2
    assert all(
        list(item) == ["baseline_commit_blob", "bytes", "index_blob", "path", "worktree_sha256"]
        for item in baseline["protected_authorities"]
    )
    destination = mirror["destination"]
    members = [
        f"{destination}/execution-source-manifest.json",
        f"{destination}/archival-receipt.json",
        *(f"{destination}/tree/{item['path']}" for item in mirror["sources"]),
        f"{destination}/tree/{mirror['launcher']['path']}",
    ]
    assert len(members) == len(set(members)) == 40
    for path in members:
        pure = PurePosixPath(path)
        assert not pure.is_absolute()
        assert ".." not in pure.parts
        assert "\\" not in path


def test_historical_import_boundary_is_static_and_unloaded() -> None:
    import sitecustomize

    historical_root = ntpath.normcase(
        ntpath.normpath(ntpath.join(os.fspath(REPO_ROOT), "historical", "phase41-source-closure"))
    )
    for entry in sys.path:
        if not entry:
            continue
        candidate = ntpath.normcase(ntpath.normpath(ntpath.abspath(entry)))
        assert candidate != historical_root
        assert not candidate.startswith(historical_root + "\\")
    assert not any(
        name == "historical.phase41_source_closure"
        or name.startswith("historical.phase41_source_closure.")
        for name in sys.modules
    )
    assert historical_root in sitecustomize.PHASE411_PROTECTED_ROOTS


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _strict_json(raw: bytes) -> dict[str, Any]:
    def reject_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise AssertionError(f"duplicate JSON key in test authority: {key}")
            result[key] = value
        return result

    value = json.loads(raw.decode("utf-8"), object_pairs_hook=reject_duplicates)
    assert isinstance(value, dict)
    return value


def _canonical_json(value: object) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        + "\n"
    ).encode("utf-8")


def _synthetic_layout(tmp_path: Path) -> archive._ArchiveLayout:
    evidence_root = tmp_path / "evidence"
    source_root = evidence_root / "clean-runtime"
    launcher_path = evidence_root / "scripts" / "phase41_one_shot_launcher.ps1"
    manifest_path = tmp_path / "repo" / "execution-source-manifest.json"
    destination = tmp_path / "historical" / ("a" * 64)
    members = {
        "src/__init__.py": b"",
        "src/example.py": "MESSAGE = 'xin chào'\n".encode("utf-8"),
    }
    launcher = b"Write-Output 'synthetic phase 41 launcher'\r\n"
    for relative, raw in members.items():
        path = source_root / PurePosixPath(relative)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
    launcher_path.parent.mkdir(parents=True, exist_ok=True)
    launcher_path.write_bytes(launcher)
    files = [
        {"bytes": len(raw), "path": relative, "sha256": _sha256(raw)}
        for relative, raw in sorted(members.items())
    ]
    manifest = {
        "alternate_evaluators_permitted": False,
        "closed_import_roots": ["src.example"],
        "files": files,
        "launcher": {
            "bytes": len(launcher),
            "path": "scripts/phase41_one_shot_launcher.ps1",
            "sha256": _sha256(launcher),
        },
        "launcher_host": {
            "bytes": 1,
            "external_launch_receipt_sha256": "1" * 64,
            "mode": "synthetic",
            "path": "C:\\synthetic\\pwsh.exe",
            "sha256": "2" * 64,
        },
        "preparation_scope": "synthetic",
        "python": {
            "bytes": 1,
            "path": "C:\\synthetic\\python.exe",
            "runtime_import_roots": ["C:\\synthetic\\site-packages"],
            "sha256": "3" * 64,
            "version": "3.13.13",
        },
        "schema_version": "phase41-execution-source-manifest-v1",
        "source_tree_sha256": "a" * 64,
        "upstream_declared_source_tree_sha256": "b" * 64,
    }
    manifest_path.parent.mkdir(parents=True)
    manifest_path.write_bytes(_canonical_json(manifest))
    destination.parent.mkdir(parents=True)
    repo_root = tmp_path / "current-repo"
    for relative, raw in members.items():
        path = repo_root / PurePosixPath(relative)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
    (repo_root / "src" / "example.py").write_text("changed\n", encoding="utf-8")
    return archive._ArchiveLayout(
        manifest_path=manifest_path,
        evidence_root=evidence_root,
        source_root=source_root,
        launcher_path=launcher_path,
        destination=destination,
        repo_root=repo_root,
        expected_manifest_sha256=_sha256(manifest_path.read_bytes()),
        expected_schema_version="phase41-execution-source-manifest-v1",
        expected_tree_sha256="a" * 64,
        expected_launcher_sha256=_sha256(launcher),
        expected_source_paths=tuple(item["path"] for item in files),
        expected_worktree_mismatches=("src/example.py",),
    )


def test_synthetic_archive_is_captured_receipted_and_verified(tmp_path: Path) -> None:
    layout = _synthetic_layout(tmp_path)
    raw_manifest = layout.manifest_path.read_bytes()

    receipt = archive._archive_bound_source_closure_for_test(layout)

    assert receipt.source_tree_sha256 == "a" * 64
    assert receipt.provenance_label == (
        "post_evaluation_archival_mirror_not_refactored_metric_producer"
    )
    assert (layout.destination / "execution-source-manifest.json").read_bytes() == raw_manifest
    assert (layout.destination / "tree/src/example.py").read_text(encoding="utf-8") == (
        "MESSAGE = 'xin chào'\n"
    )
    assert (layout.destination / "archival-receipt.json").is_file()
    assert receipt.current_worktree_mismatches[0]["path"] == "src/example.py"
    assert archive._verify_archived_source_closure_for_test(layout) == receipt


def test_archive_cli_is_successful_on_legacy_console(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    class StrictLegacyConsole:
        encoding = "cp1252"

        def __init__(self) -> None:
            self.text = ""

        def write(self, value: str) -> int:
            value.encode(self.encoding, errors="strict")
            self.text += value
            return len(value)

        def flush(self) -> None:
            return None

    class SyntheticReceipt:
        @staticmethod
        def as_dict() -> dict[str, str]:
            return {"archive_destination": os.fspath(tmp_path / "bài tập")}

    console = StrictLegacyConsole()
    monkeypatch.setattr(archive, "verify_archived_source_closure", SyntheticReceipt)
    monkeypatch.setattr(archive.sys, "stdout", console)

    assert archive.main(["verify"]) == 0
    assert "\\u1eadp" in console.text
    assert console.text.endswith("\n")


@pytest.mark.parametrize(
    ("mutation", "match"),
    [
        ("schema", "schema"),
        ("tree", "tree"),
        ("source_hash", "hash"),
        ("missing_source", "missing"),
        ("extra_manifest_member", "membership"),
        ("path_escape", "path"),
    ],
)
def test_archive_rejects_invalid_manifest_or_source_before_publication(
    tmp_path: Path,
    mutation: str,
    match: str,
) -> None:
    layout = _synthetic_layout(tmp_path)
    manifest = _strict_json(layout.manifest_path.read_bytes())
    if mutation == "schema":
        manifest["schema_version"] = "wrong"
    elif mutation == "tree":
        manifest["source_tree_sha256"] = "f" * 64
    elif mutation == "source_hash":
        (layout.source_root / "src/example.py").write_text("tampered\n", encoding="utf-8")
    elif mutation == "missing_source":
        (layout.source_root / "src/example.py").unlink()
    elif mutation == "extra_manifest_member":
        manifest["files"].append(
            {"bytes": 0, "path": "src/extra.py", "sha256": _sha256(b"")}
        )
    elif mutation == "path_escape":
        manifest["files"][0]["path"] = "../escape.py"
    if mutation in {"schema", "tree", "extra_manifest_member", "path_escape"}:
        layout.manifest_path.write_bytes(_canonical_json(manifest))
        layout = replace(layout, expected_manifest_sha256=_sha256(layout.manifest_path.read_bytes()))

    with pytest.raises(archive.ArchiveError, match=match):
        archive._archive_bound_source_closure_for_test(layout)

    assert not layout.destination.exists()


def test_archive_rejects_duplicate_json_keys_and_destination_collision(tmp_path: Path) -> None:
    layout = _synthetic_layout(tmp_path)
    raw = layout.manifest_path.read_bytes()
    layout.manifest_path.write_bytes(b'{"schema_version":"duplicate",' + raw[1:])
    layout = replace(layout, expected_manifest_sha256=_sha256(layout.manifest_path.read_bytes()))
    with pytest.raises(archive.ArchiveError, match="duplicate JSON key"):
        archive._archive_bound_source_closure_for_test(layout)
    assert not layout.destination.exists()

    layout = _synthetic_layout(tmp_path / "collision")
    layout.destination.mkdir(parents=True)
    marker = layout.destination / "do-not-overwrite.txt"
    marker.write_text("preserve", encoding="utf-8")
    with pytest.raises(archive.ArchiveError, match="destination"):
        archive._archive_bound_source_closure_for_test(layout)
    assert marker.read_text(encoding="utf-8") == "preserve"


def test_archive_rejects_overlap_and_redirecting_source_ancestry(tmp_path: Path) -> None:
    layout = _synthetic_layout(tmp_path / "overlap")
    overlapping = replace(layout, destination=layout.source_root / "archive")
    with pytest.raises(archive.ArchiveError, match="overlap"):
        archive._archive_bound_source_closure_for_test(overlapping)

    layout = _synthetic_layout(tmp_path / "redirect")
    real = layout.evidence_root / "real-clean-runtime"
    layout.source_root.rename(real)
    try:
        layout.source_root.symlink_to(real, target_is_directory=True)
    except OSError as exc:  # pragma: no cover - host policy, not product behavior
        pytest.fail(f"test host cannot create the required temp symlink: {exc}")
    with pytest.raises(archive.ArchiveError, match="redirect|reparse|symlink"):
        archive._archive_bound_source_closure_for_test(layout)
    assert not layout.destination.exists()


def test_archive_rejects_redirecting_destination_parent(tmp_path: Path) -> None:
    layout = _synthetic_layout(tmp_path)
    redirected_parent = layout.destination.parent
    real_parent = redirected_parent.with_name("real-historical")
    redirected_parent.rename(real_parent)
    try:
        redirected_parent.symlink_to(real_parent, target_is_directory=True)
    except OSError as exc:  # pragma: no cover - host policy, not product behavior
        pytest.fail(f"test host cannot create the required temp symlink: {exc}")
    with pytest.raises(archive.ArchiveError, match="destination.*redirect|symlink|reparse"):
        archive._archive_bound_source_closure_for_test(layout)


def _assert_archive_ancestor_swap_is_contained(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    event: str,
) -> None:
    layout = _synthetic_layout(tmp_path)
    parent = layout.destination.parent
    moved_parent = parent.with_name(f"{parent.name}-{event}-moved")
    outside = tmp_path / f"outside-{event}"
    outside.mkdir()
    outcome = {"attempted": False, "blocked": False, "swapped": False}

    def swap_ancestor(current_event: str, _target: Path) -> None:
        if current_event != event or outcome["attempted"]:
            return
        outcome["attempted"] = True
        try:
            parent.rename(moved_parent)
        except OSError:
            outcome["blocked"] = True
            return
        parent.symlink_to(outside, target_is_directory=True)
        outcome["swapped"] = True

    monkeypatch.setattr(archive, "_publication_test_hook", swap_ancestor)
    try:
        receipt = archive._archive_bound_source_closure_for_test(layout)
    except archive.ArchiveError as exc:
        assert "parent binding changed" in str(exc)
        assert outcome == {"attempted": True, "blocked": False, "swapped": True}
        assert not layout.destination.exists()
    else:
        assert receipt.source_tree_sha256 == "a" * 64
        assert outcome == {"attempted": True, "blocked": True, "swapped": False}
        assert layout.destination.is_dir()
    assert tuple(outside.iterdir()) == ()


def test_archive_stage_creation_is_bound_against_ancestor_swap(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _assert_archive_ancestor_swap_is_contained(tmp_path, monkeypatch, "stage_creation")


def test_archive_member_write_is_bound_against_ancestor_swap(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _assert_archive_ancestor_swap_is_contained(tmp_path, monkeypatch, "member_write")


def test_archive_final_rename_is_bound_against_ancestor_swap(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _assert_archive_ancestor_swap_is_contained(tmp_path, monkeypatch, "final_rename")


def test_failed_archive_publication_keeps_final_destination_retryable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    layout = _synthetic_layout(tmp_path)
    implementation = archive._write_exclusive
    calls = 0

    def fail_after_first_member(
        binding: archive._PublicationBinding, relative: Path, raw: bytes
    ) -> None:
        nonlocal calls
        calls += 1
        if calls == 2:
            raise archive.ArchiveError("synthetic staging failure")
        implementation(binding, relative, raw)

    monkeypatch.setattr(archive, "_write_exclusive", fail_after_first_member)
    with pytest.raises(archive.ArchiveError, match="synthetic staging failure"):
        archive._archive_bound_source_closure_for_test(layout)
    assert not layout.destination.exists()
    assert list(layout.destination.parent.glob(f".{layout.destination.name}.staging-*"))

    monkeypatch.setattr(archive, "_write_exclusive", implementation)
    archive._archive_bound_source_closure_for_test(layout)
    assert layout.destination.is_dir()


def test_archived_extra_member_and_byte_drift_fail_verification(tmp_path: Path) -> None:
    layout = _synthetic_layout(tmp_path)
    archive._archive_bound_source_closure_for_test(layout)
    extra = layout.destination / "tree/src/extra.py"
    extra.write_text("extra\n", encoding="utf-8")
    with pytest.raises(archive.ArchiveError, match="extra|membership"):
        archive._verify_archived_source_closure_for_test(layout)
    extra.unlink()
    (layout.destination / "tree/src/example.py").write_text("drift\n", encoding="utf-8")
    with pytest.raises(archive.ArchiveError, match="hash|bytes"):
        archive._verify_archived_source_closure_for_test(layout)


def test_archive_verification_rejects_non_file_and_root_members(tmp_path: Path) -> None:
    layout = _synthetic_layout(tmp_path / "empty")
    archive._archive_bound_source_closure_for_test(layout)
    empty = layout.destination / "tree" / "unexpected-empty"
    empty.mkdir()
    with pytest.raises(archive.ArchiveError, match="membership"):
        archive._verify_archived_source_closure_for_test(layout)

    layout = _synthetic_layout(tmp_path / "link")
    archive._archive_bound_source_closure_for_test(layout)
    link = layout.destination / "tree" / "redirect.py"
    try:
        link.symlink_to(layout.destination / "tree/src/example.py")
    except OSError as exc:  # pragma: no cover - host policy, not product behavior
        pytest.fail(f"test host cannot create the required temp symlink: {exc}")
    with pytest.raises(archive.ArchiveError, match="link|reparse"):
        archive._verify_archived_source_closure_for_test(layout)

    layout = _synthetic_layout(tmp_path / "root")
    archive._archive_bound_source_closure_for_test(layout)
    (layout.destination / "unexpected-root.txt").write_text("extra", encoding="utf-8")
    with pytest.raises(archive.ArchiveError, match="root membership"):
        archive._verify_archived_source_closure_for_test(layout)


def test_receipt_self_hash_cannot_rebind_false_mismatch_facts(tmp_path: Path) -> None:
    layout = _synthetic_layout(tmp_path)
    archive._archive_bound_source_closure_for_test(layout)
    receipt_path = layout.destination / "archival-receipt.json"
    receipt = _strict_json(receipt_path.read_bytes())
    receipt["current_worktree_mismatches"][0]["expected_sha256"] = "f" * 64
    unsigned = dict(receipt)
    unsigned.pop("receipt_sha256")
    receipt["receipt_sha256"] = _sha256(_canonical_json(unsigned))
    receipt_path.write_bytes(_canonical_json(receipt))
    with pytest.raises(archive.ArchiveError, match="source manifest"):
        archive._verify_archived_source_closure_for_test(layout)


def test_production_entry_points_are_fixed_and_accept_no_paths() -> None:
    assert os.fspath(archive.PRODUCTION_SOURCE_ROOT) == (
        "C:\\ProgramData\\VNPhish\\phase41-evaluation-evidence\\clean-runtime"
    )
    assert os.fspath(archive.PRODUCTION_LAUNCHER_PATH) == (
        "C:\\ProgramData\\VNPhish\\phase41-evaluation-evidence\\scripts\\"
        "phase41_one_shot_launcher.ps1"
    )
    assert not __import__("inspect").signature(
        archive.archive_bound_source_closure
    ).parameters
    assert not __import__("inspect").signature(
        archive.verify_archived_source_closure
    ).parameters


@pytest.mark.parametrize("token", ("NaN", "Infinity", "-Infinity"))
def test_archive_json_reader_rejects_non_finite_tokens(token: str) -> None:
    raw = ('{"value":' + token + "}").encode("utf-8")
    with pytest.raises(archive.ArchiveError, match="non-standard JSON token"):
        archive._strict_json(raw, where="synthetic archive document")


def test_precollection_guard_blocks_before_underlying_filesystem_call(tmp_path: Path) -> None:
    import builtins
    import sitecustomize

    protected = Path(sitecustomize.PHASE411_PROTECTED_PREFIX) / "test.jsonl"
    before = sitecustomize.phase411_guard_snapshot()
    with pytest.raises(PermissionError, match="forbidden authority path"):
        protected.read_bytes()
    after = sitecustomize.phase411_guard_snapshot()
    assert len(after["rejected"]) == len(before["rejected"]) + 1
    assert after["underlying_forbidden"] == []

    keyword_attempts = (
        lambda: builtins.open(file=protected),
        lambda: os.stat(path=protected),
        lambda: os.rename(src=protected, dst=tmp_path / "never-created.jsonl"),
    )
    before_keywords = sitecustomize.phase411_guard_snapshot()
    for attempt in keyword_attempts:
        with pytest.raises(PermissionError, match="forbidden authority path"):
            attempt()
    after_keywords = sitecustomize.phase411_guard_snapshot()
    assert len(after_keywords["rejected"]) == len(before_keywords["rejected"]) + 3
    assert after_keywords["underlying_forbidden"] == []

    nearby = tmp_path / "data" / "splits-lookalike" / "safe.txt"
    nearby.parent.mkdir(parents=True)
    nearby.write_text("safe", encoding="utf-8")
    assert nearby.read_text(encoding="utf-8") == "safe"


def test_deny_open_guard_covers_metadata_and_link_path_apis() -> None:
    import sitecustomize

    protected = Path(sitecustomize.PHASE411_PROTECTED_PREFIX) / "synthetic.jsonl"
    attempts = (
        lambda: os.access(protected, os.F_OK),
        lambda: os.chmod(protected, 0o600),
        lambda: os.link(protected, protected.with_suffix(".link")),
        lambda: os.symlink(protected, protected.with_suffix(".symlink")),
        lambda: protected.chmod(0o600),
    )
    for attempt in attempts:
        with pytest.raises(PermissionError, match="forbidden authority path"):
            attempt()

    with pytest.raises(PermissionError, match="process execution denied"):
        subprocess.run(["synthetic-never-launched"], check=False)
    assert sitecustomize.phase411_guard_snapshot()["underlying_forbidden"] == []


def test_deny_open_guard_blocks_descriptors_and_process_calls() -> None:
    import sitecustomize

    with pytest.raises(PermissionError, match="descriptor-relative"):
        os.open("synthetic-relative.jsonl", os.O_RDONLY, dir_fd=12345)
    unknown = max(sitecustomize.phase411_descriptor_capabilities(), default=100) + 10000
    for attempt in (
        lambda: os.fstat(unknown),
        lambda: os.fstat(fd=unknown),
        lambda: open(file=unknown, mode="rb"),
    ):
        with pytest.raises(PermissionError, match="descriptor capability denied"):
            attempt()
    with pytest.raises(PermissionError, match="process execution denied"):
        subprocess.run(["synthetic-never-launched"], check=False)

    assert sitecustomize.phase411_guard_snapshot()["underlying_forbidden"] == []
