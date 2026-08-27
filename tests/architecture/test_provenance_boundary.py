"""Provenance and held-out-data boundary tests for Phase 41.1 Plan 01."""

from __future__ import annotations

from dataclasses import replace
import hashlib
import importlib.util
import json
import os
from pathlib import Path, PurePosixPath
import subprocess
import sys
from typing import Any

import pytest

from scripts import archive_phase41_source_closure as archive


REPO_ROOT = Path(__file__).parents[2]
FIXTURE_PATH = Path(__file__).parent / "fixtures" / "protected_authority_baseline.json"


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
    with pytest.raises(PermissionError, match="Phase 41.1 forbidden path"):
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
        with pytest.raises(PermissionError, match="Phase 41.1 forbidden path"):
            attempt()
    after_keywords = sitecustomize.phase411_guard_snapshot()
    assert len(after_keywords["rejected"]) == len(before_keywords["rejected"]) + 3
    assert after_keywords["underlying_forbidden"] == []

    nearby = tmp_path / "data" / "splits-lookalike" / "safe.txt"
    nearby.parent.mkdir(parents=True)
    nearby.write_text("safe", encoding="utf-8")
    assert nearby.read_text(encoding="utf-8") == "safe"


def test_guard_is_active_during_adversarial_collection_and_in_child_python(
    tmp_path: Path,
) -> None:
    attack = tmp_path / "test_collection_attack.py"
    attack.write_text(
        "from pathlib import Path\n"
        "import sitecustomize\n"
        "ATTACK = Path(sitecustomize.PHASE411_PROTECTED_PREFIX) / 'test.jsonl'\n"
        "try:\n"
        "    open(file=ATTACK, encoding='utf-8')\n"
        "except PermissionError:\n"
        "    COLLECTION_BLOCKED = True\n"
        "else:\n"
        "    raise AssertionError('collection-time forbidden open reached filesystem')\n"
        "def test_collection_guard():\n"
        "    assert COLLECTION_BLOCKED\n"
        "    assert sitecustomize.phase411_guard_snapshot()['underlying_forbidden'] == []\n",
        encoding="utf-8",
    )
    collected = subprocess.run(
        [sys.executable, "-m", "pytest", os.fspath(attack), "-q", "-p", "no:cacheprovider"],
        cwd=tmp_path,
        env=os.environ.copy(),
        capture_output=True,
        text=True,
        check=False,
    )
    assert collected.returncode == 0, collected.stdout + collected.stderr

    child_code = (
        "from pathlib import Path; import json, os, sitecustomize; "
        "p=Path(sitecustomize.PHASE411_PROTECTED_PREFIX)/'test.jsonl'; "
        "blocked=False; "
        "\ntry: os.stat(path=p)\nexcept PermissionError: blocked=True\n"
        "print(json.dumps({'blocked': blocked, "
        "'snapshot': sitecustomize.phase411_guard_snapshot()}))"
    )
    child = subprocess.run(
        [sys.executable, "-c", child_code],
        cwd=tmp_path,
        env=os.environ.copy(),
        capture_output=True,
        text=True,
        check=False,
    )
    assert child.returncode == 0, child.stderr
    payload = json.loads(child.stdout)
    assert payload["blocked"] is True
    assert payload["snapshot"]["underlying_forbidden"] == []

    attestation = tmp_path / "guard_attestation.py"
    attestation.write_text(
        "import json, sitecustomize\n"
        "print(json.dumps({'installed': sitecustomize.PHASE411_GUARD_INSTALLED}))\n",
        encoding="utf-8",
    )
    script_child = subprocess.run(
        [sys.executable, os.fspath(attestation)],
        cwd=tmp_path,
        env=os.environ.copy(),
        capture_output=True,
        text=True,
        check=False,
    )
    assert script_child.returncode == 0, script_child.stderr
    assert json.loads(script_child.stdout) == {"installed": True}


def test_deny_open_guard_rejects_child_bootstrap_bypasses(
    tmp_path: Path,
) -> None:
    guarded_env = os.environ.copy()
    for flag in ("-S", "-I", "-E"):
        with pytest.raises(PermissionError, match="disable site or environment"):
            subprocess.run([sys.executable, flag, "-c", "pass"], check=False)

    without_sentinel = dict(guarded_env)
    without_sentinel.pop("PHASE411_DENY_OPEN_SENTINEL", None)
    with pytest.raises(PermissionError, match="deny-open sentinel"):
        subprocess.run(
            [sys.executable, "-c", "pass"],
            env=without_sentinel,
            check=False,
        )
    with pytest.raises(PermissionError, match="deny-open sentinel"):
        subprocess.run([sys.executable, "-c", "pass"], env={}, check=False)
    with pytest.raises(PermissionError, match="executable override"):
        subprocess.run(
            [sys.executable, "-c", "pass"],
            executable=sys.executable,
            env=guarded_env,
            check=False,
        )

    without_bootstrap = dict(guarded_env)
    without_bootstrap["PYTHONPATH"] = os.fspath(tmp_path)
    with pytest.raises(PermissionError, match="deny-open bootstrap"):
        subprocess.run(
            [sys.executable, "-c", "pass"],
            env=without_bootstrap,
            check=False,
        )


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
        with pytest.raises(PermissionError, match="forbidden path"):
            attempt()

    with pytest.raises(PermissionError, match="read-only allowlist"):
        subprocess.run(["git", "status"], check=False)
    assert sitecustomize.phase411_guard_snapshot()["underlying_forbidden"] == []


def test_deny_open_guard_blocks_descriptors_and_non_python_subprocesses() -> None:
    import sitecustomize

    with pytest.raises(PermissionError, match="descriptor-relative"):
        os.open("synthetic-relative.jsonl", os.O_RDONLY, dir_fd=12345)
    if not sitecustomize._INHERITED_FDS:
        pytest.skip("no inherited descriptors are open in this process")
    with pytest.raises(PermissionError, match="inherited file descriptor"):
        open(next(iter(sitecustomize._INHERITED_FDS)), "rb")
    with pytest.raises(PermissionError, match="non-Python subprocess"):
        subprocess.run(
            [os.environ.get("COMSPEC", "cmd.exe"), "/c", "echo", "synthetic"],
            check=False,
        )

    assert sitecustomize.phase411_guard_snapshot()["underlying_forbidden"] == []


def test_protected_authorities_match_fixed_baseline() -> None:
    baseline = _strict_json(FIXTURE_PATH.read_bytes())
    commit = baseline["baseline_commit"]
    for authority in baseline["protected_authorities"]:
        relative = authority["path"]
        raw = (REPO_ROOT / PurePosixPath(relative)).read_bytes()
        assert len(raw) == authority["bytes"]
        assert _sha256(raw) == authority["worktree_sha256"]
        staged = subprocess.run(
            ["git", "ls-files", "--stage", "--", relative],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=True,
        ).stdout.split()
        assert staged[1] == authority["index_blob"]
        historical = subprocess.run(
            ["git", "rev-parse", f"{commit}:{relative}"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
        assert historical == authority["baseline_commit_blob"]

    mirror = baseline["historical_mirror"]
    manifest_authority = baseline["protected_authorities"][0]
    manifest = _strict_json((REPO_ROOT / manifest_authority["path"]).read_bytes())
    expected_sources = [
        {"bytes": item["bytes"], "path": item["path"], "sha256": item["sha256"]}
        for item in manifest["files"]
    ]
    assert manifest["schema_version"] == mirror["manifest_schema_version"]
    assert manifest["source_tree_sha256"] == mirror["source_tree_sha256"]
    assert expected_sources == mirror["sources"]
    assert manifest["launcher"] == mirror["launcher"]

    if os.environ.get("PHASE411_REQUIRE_HISTORICAL_ARCHIVE") == "1":
        destination = REPO_ROOT / PurePosixPath(mirror["destination"])
        expected = {
            "execution-source-manifest.json": manifest_authority["worktree_sha256"],
            **{f"tree/{item['path']}": item["sha256"] for item in mirror["sources"]},
            f"tree/{mirror['launcher']['path']}": mirror["launcher"]["sha256"],
        }
        actual = {
            path.relative_to(destination).as_posix()
            for path in destination.rglob("*")
            if path.is_file()
        }
        assert actual == set(expected) | {"archival-receipt.json"}
        for relative, expected_sha in expected.items():
            archived_path = destination / PurePosixPath(relative)
            assert _sha256(archived_path.read_bytes()) == expected_sha
            repository_relative = archived_path.relative_to(REPO_ROOT).as_posix()
            staged = subprocess.run(
                ["git", "ls-files", "--stage", "--", repository_relative],
                cwd=REPO_ROOT,
                capture_output=True,
                text=True,
                check=True,
            ).stdout.split()
            assert staged, f"historical mirror is not staged: {repository_relative}"
            blob = subprocess.run(
                ["git", "cat-file", "blob", staged[1]],
                cwd=REPO_ROOT,
                capture_output=True,
                check=True,
            ).stdout
            assert _sha256(blob) == expected_sha

        archive_root = os.path.normcase(os.path.abspath(destination))
        assert all(
            os.path.normcase(os.path.abspath(entry)) != archive_root
            for entry in sys.path
            if entry
        )
        assert importlib.util.find_spec("historical.phase41_source_closure") is None
