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


def test_precollection_guard_blocks_before_underlying_filesystem_call(tmp_path: Path) -> None:
    import sitecustomize

    protected = Path(sitecustomize.PHASE411_PROTECTED_PREFIX) / "test.jsonl"
    before = sitecustomize.phase411_guard_snapshot()
    with pytest.raises(PermissionError, match="Phase 41.1 forbidden path"):
        protected.read_bytes()
    after = sitecustomize.phase411_guard_snapshot()
    assert len(after["rejected"]) == len(before["rejected"]) + 1
    assert after["underlying_forbidden"] == []

    nearby = tmp_path / "data" / "splits-lookalike" / "safe.txt"
    nearby.parent.mkdir(parents=True)
    nearby.write_text("safe", encoding="utf-8")
    assert nearby.read_text(encoding="utf-8") == "safe"


def test_guard_is_active_during_adversarial_collection_and_in_child_python(
    tmp_path: Path,
) -> None:
    attack = tmp_path / "test_collection_attack.py"
    attack.write_text(
        """from pathlib import Path\n"
        "import sitecustomize\n"
        "ATTACK = Path(sitecustomize.PHASE411_PROTECTED_PREFIX) / 'test.jsonl'\n"
        "try:\n"
        "    ATTACK.read_text(encoding='utf-8')\n"
        "except PermissionError:\n"
        "    COLLECTION_BLOCKED = True\n"
        "else:\n"
        "    raise AssertionError('collection-time forbidden open reached filesystem')\n"
        "def test_collection_guard():\n"
        "    assert COLLECTION_BLOCKED\n"
        "    assert sitecustomize.phase411_guard_snapshot()['underlying_forbidden'] == []\n"
        """,
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
        "from pathlib import Path; import json, sitecustomize; "
        "p=Path(sitecustomize.PHASE411_PROTECTED_PREFIX)/'test.jsonl'; "
        "blocked=False; "
        "\ntry: p.stat()\nexcept PermissionError: blocked=True\n"
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
            assert _sha256((destination / PurePosixPath(relative)).read_bytes()) == expected_sha

        archive_root = os.path.normcase(os.path.abspath(destination))
        assert all(
            os.path.normcase(os.path.abspath(entry)) != archive_root
            for entry in sys.path
            if entry
        )
        assert importlib.util.find_spec("historical.phase41_source_closure") is None

