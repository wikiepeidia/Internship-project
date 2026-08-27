"""Synthetic compatibility contract for the source-archiving domain."""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
from typing import Any

import pytest

from scripts import archive_phase41_source_closure as archive


REPO_ROOT = Path(__file__).parents[2]
ACTIVE_TEXT_FIXTURE = REPO_ROOT / "tests/architecture/fixtures/active_text_contract.json"
TOOL_FIXTURE = REPO_ROOT / "tests/architecture/fixtures/tool_inventory_contract.json"

EXPECTED_SOURCE_PATHS = (
    "src/__init__.py",
    "src/config/__init__.py",
    "src/config/settings.py",
    "src/data_pipeline/__init__.py",
    "src/data_pipeline/schemas.py",
    "src/model_adaptation/__init__.py",
    "src/model_adaptation/catalog.py",
    "src/model_adaptation/cli.py",
    "src/model_adaptation/convert.py",
    "src/model_adaptation/data.py",
    "src/model_adaptation/doctor.py",
    "src/model_adaptation/phase40_callbacks.py",
    "src/model_adaptation/phase40_comparison_launch.py",
    "src/model_adaptation/phase40_contract.py",
    "src/model_adaptation/phase40_evidence.py",
    "src/model_adaptation/phase40_final_authority.py",
    "src/model_adaptation/phase40_gguf.py",
    "src/model_adaptation/phase40_graphs.py",
    "src/model_adaptation/phase40_handoff.py",
    "src/model_adaptation/phase40_metrics.py",
    "src/model_adaptation/phase40_modes.py",
    "src/model_adaptation/phase40_notebooks.py",
    "src/model_adaptation/phase40_phobert_release.py",
    "src/model_adaptation/phase40_production_authorities.py",
    "src/model_adaptation/phase40_release_authorities.py",
    "src/model_adaptation/phase40_review.py",
    "src/model_adaptation/phase40_runtime_materialize.py",
    "src/model_adaptation/phase41_evaluation.py",
    "src/model_adaptation/phase41_protocols.py",
    "src/model_adaptation/phobert_training.py",
    "src/model_adaptation/pilot.py",
    "src/model_adaptation/prompts.py",
    "src/model_adaptation/registry.py",
    "src/model_adaptation/schemas.py",
    "src/model_adaptation/training.py",
    "src/runtime/__init__.py",
    "src/runtime/contracts.py",
)

# Literal, test-owned archive tool rows. These do not derive from source or policy.
PRE_ARCHIVE_TOOL = {
    "path": "scripts/archive_phase41_source_closure.py",
    "lifecycle": "compatibility",
    "language": "python",
    "kind": "provenance_cli",
    "phase_language": "phase_41",
    "imports": [
        "__future__", "argparse", "contextlib", "dataclasses", "datetime",
        "hashlib", "json", "os", "pathlib", "re", "secrets",
        "src.core_binding", "stat", "sys", "typing",
    ],
    "routes": [],
}
POST_ARCHIVE_TOOL = {
    "path": "scripts/archive_phase41_source_closure.py",
    "lifecycle": "compatibility",
    "language": "python",
    "kind": "provenance_cli",
    "phase_language": "phase_41",
    "imports": [
        "__future__", "argparse", "contextlib", "dataclasses", "datetime",
        "hashlib", "json", "os", "pathlib", "re", "secrets",
        "src.source_archiving", "stat", "sys", "typing",
    ],
    "routes": [],
}

# Rows are (id, path, literal, owner_symbol, reason, lifecycle). Keeping the
# complete PRE and POST authorities here makes mixed-state mutations observable.
PRE_ACTIVE_OWNERS = (
    ("terminal-result-schema", "src/modeling/evaluation.py", "phase41-one-shot-results-v1", "TwoModelEvaluationResult.schema_version", "preserve terminal two-model result schema compatibility", "active"),
    ("evidence-manifest-schema", "src/modeling/evidence.py", "phase41-evidence-manifest-v1", "_artifact_hashes", "preserve sealed evidence manifest schema compatibility", "active"),
    ("source-manifest-schema-validator", "src/modeling/evidence.py", "phase41-execution-source-manifest-v1", "_validate_source_chain", "preserve execution source manifest schema compatibility", "active"),
    ("materialization-schema-validator", "src/modeling/evidence.py", "phase41-execution-materialization-v1", "_validate_source_chain", "preserve locked runtime materialization schema compatibility", "active"),
    ("provenance-erratum-schema", "src/modeling/evidence.py", "phase41-provenance-erratum-v1", "_validate_erratum", "preserve corrective provenance erratum schema compatibility", "active"),
    ("legacy-release-artifact-glob", "src/runtime/doctor.py", "phase5-release-eval-*.json", "RELEASE_MANIFEST_PATTERNS", "preserve legacy release-evaluation artifact discovery", "active"),
    ("archive-facade-description", "scripts/archive_phase41_source_closure.py", "Archive and verify the exact source closure that produced Phase 41 evidence.", "<module>.__doc__", "characterize pre-extraction facade description until authorized domain rewrite", "compatibility"),
    ("archive-source-manifest-schema", "scripts/archive_phase41_source_closure.py", "phase41-execution-source-manifest-v1", "EXPECTED_SCHEMA_VERSION", "preserve immutable source-closure schema compatibility", "compatibility"),
    ("archive-receipt-schema", "scripts/archive_phase41_source_closure.py", "phase411-source-closure-archival-receipt-v1", "RECEIPT_SCHEMA_VERSION", "preserve immutable archival receipt schema compatibility", "compatibility"),
    ("archive-provenance-label", "scripts/archive_phase41_source_closure.py", "post_evaluation_archival_mirror_not_refactored_metric_producer", "PROVENANCE_LABEL", "preserve immutable post-evaluation archival provenance", "compatibility"),
    ("archive-source-phase40-callbacks", "scripts/archive_phase41_source_closure.py", "src/model_adaptation/phase40_callbacks.py", "_SOURCE_PATHS", "preserve immutable source-closure member identity", "compatibility"),
    ("archive-source-phase40-comparison-launch", "scripts/archive_phase41_source_closure.py", "src/model_adaptation/phase40_comparison_launch.py", "_SOURCE_PATHS", "preserve immutable source-closure member identity", "compatibility"),
    ("archive-source-phase40-contract", "scripts/archive_phase41_source_closure.py", "src/model_adaptation/phase40_contract.py", "_SOURCE_PATHS", "preserve immutable source-closure member identity", "compatibility"),
    ("archive-source-phase40-evidence", "scripts/archive_phase41_source_closure.py", "src/model_adaptation/phase40_evidence.py", "_SOURCE_PATHS", "preserve immutable source-closure member identity", "compatibility"),
    ("archive-source-phase40-final-authority", "scripts/archive_phase41_source_closure.py", "src/model_adaptation/phase40_final_authority.py", "_SOURCE_PATHS", "preserve immutable source-closure member identity", "compatibility"),
    ("archive-source-phase40-gguf", "scripts/archive_phase41_source_closure.py", "src/model_adaptation/phase40_gguf.py", "_SOURCE_PATHS", "preserve immutable source-closure member identity", "compatibility"),
    ("archive-source-phase40-graphs", "scripts/archive_phase41_source_closure.py", "src/model_adaptation/phase40_graphs.py", "_SOURCE_PATHS", "preserve immutable source-closure member identity", "compatibility"),
    ("archive-source-phase40-handoff", "scripts/archive_phase41_source_closure.py", "src/model_adaptation/phase40_handoff.py", "_SOURCE_PATHS", "preserve immutable source-closure member identity", "compatibility"),
    ("archive-source-phase40-metrics", "scripts/archive_phase41_source_closure.py", "src/model_adaptation/phase40_metrics.py", "_SOURCE_PATHS", "preserve immutable source-closure member identity", "compatibility"),
    ("archive-source-phase40-modes", "scripts/archive_phase41_source_closure.py", "src/model_adaptation/phase40_modes.py", "_SOURCE_PATHS", "preserve immutable source-closure member identity", "compatibility"),
    ("archive-source-phase40-notebooks", "scripts/archive_phase41_source_closure.py", "src/model_adaptation/phase40_notebooks.py", "_SOURCE_PATHS", "preserve immutable source-closure member identity", "compatibility"),
    ("archive-source-phase40-phobert-release", "scripts/archive_phase41_source_closure.py", "src/model_adaptation/phase40_phobert_release.py", "_SOURCE_PATHS", "preserve immutable source-closure member identity", "compatibility"),
    ("archive-source-phase40-production-authorities", "scripts/archive_phase41_source_closure.py", "src/model_adaptation/phase40_production_authorities.py", "_SOURCE_PATHS", "preserve immutable source-closure member identity", "compatibility"),
    ("archive-source-phase40-release-authorities", "scripts/archive_phase41_source_closure.py", "src/model_adaptation/phase40_release_authorities.py", "_SOURCE_PATHS", "preserve immutable source-closure member identity", "compatibility"),
    ("archive-source-phase40-review", "scripts/archive_phase41_source_closure.py", "src/model_adaptation/phase40_review.py", "_SOURCE_PATHS", "preserve immutable source-closure member identity", "compatibility"),
    ("archive-source-phase40-runtime-materialize", "scripts/archive_phase41_source_closure.py", "src/model_adaptation/phase40_runtime_materialize.py", "_SOURCE_PATHS", "preserve immutable source-closure member identity", "compatibility"),
    ("archive-source-phase41-evaluation", "scripts/archive_phase41_source_closure.py", "src/model_adaptation/phase41_evaluation.py", "_SOURCE_PATHS", "preserve immutable source-closure member identity", "compatibility"),
    ("archive-source-phase41-protocols", "scripts/archive_phase41_source_closure.py", "src/model_adaptation/phase41_protocols.py", "_SOURCE_PATHS", "preserve immutable source-closure member identity", "compatibility"),
    ("archive-worktree-phase41-evaluation", "scripts/archive_phase41_source_closure.py", "src/model_adaptation/phase41_evaluation.py", "_WORKTREE_MISMATCHES", "preserve immutable worktree-mismatch member identity", "compatibility"),
    ("archive-production-evidence-root", "scripts/archive_phase41_source_closure.py", r"C:\ProgramData\VNPhish\phase41-evaluation-evidence", "PRODUCTION_EVIDENCE_ROOT", "preserve immutable production evidence authority identity", "compatibility"),
    ("archive-production-launcher-filename", "scripts/archive_phase41_source_closure.py", "phase41_one_shot_launcher.ps1", "PRODUCTION_LAUNCHER_PATH", "preserve immutable production launcher filename", "compatibility"),
    ("archive-production-manifest-root", "scripts/archive_phase41_source_closure.py", "data/models/phase41/verified-export", "PRODUCTION_MANIFEST_PATH", "preserve immutable verified-export manifest root", "compatibility"),
    ("archive-production-destination-root", "scripts/archive_phase41_source_closure.py", "historical/phase41-source-closure", "PRODUCTION_DESTINATION", "preserve immutable archive destination root", "compatibility"),
    ("archive-launcher-relative-path", "scripts/archive_phase41_source_closure.py", "scripts/phase41_one_shot_launcher.ps1", "_manifest_records", "preserve immutable launcher manifest identity", "compatibility"),
)

POST_ACTIVE_OWNERS = (
    ("terminal-result-schema", "src/modeling/evaluation.py", "phase41-one-shot-results-v1", "TwoModelEvaluationResult.schema_version", "preserve terminal two-model result schema compatibility", "active"),
    ("evidence-manifest-schema", "src/modeling/evidence.py", "phase41-evidence-manifest-v1", "_artifact_hashes", "preserve sealed evidence manifest schema compatibility", "active"),
    ("source-manifest-schema-validator", "src/modeling/evidence.py", "phase41-execution-source-manifest-v1", "_validate_source_chain", "preserve execution source manifest schema compatibility", "active"),
    ("materialization-schema-validator", "src/modeling/evidence.py", "phase41-execution-materialization-v1", "_validate_source_chain", "preserve locked runtime materialization schema compatibility", "active"),
    ("provenance-erratum-schema", "src/modeling/evidence.py", "phase41-provenance-erratum-v1", "_validate_erratum", "preserve corrective provenance erratum schema compatibility", "active"),
    ("legacy-release-artifact-glob", "src/runtime/doctor.py", "phase5-release-eval-*.json", "RELEASE_MANIFEST_PATTERNS", "preserve legacy release-evaluation artifact discovery", "active"),
    ("archive-source-manifest-schema", "src/source_archiving/contracts.py", "phase41-execution-source-manifest-v1", "EXPECTED_SCHEMA_VERSION", "preserve immutable source-closure schema compatibility", "active"),
    ("archive-receipt-schema", "src/source_archiving/contracts.py", "phase411-source-closure-archival-receipt-v1", "RECEIPT_SCHEMA_VERSION", "preserve immutable archival receipt schema compatibility", "active"),
    ("archive-provenance-label", "src/source_archiving/contracts.py", "post_evaluation_archival_mirror_not_refactored_metric_producer", "PROVENANCE_LABEL", "preserve immutable post-evaluation archival provenance", "active"),
    ("archive-source-phase40-callbacks", "src/source_archiving/contracts.py", "src/model_adaptation/phase40_callbacks.py", "_SOURCE_PATHS", "preserve immutable source-closure member identity", "active"),
    ("archive-source-phase40-comparison-launch", "src/source_archiving/contracts.py", "src/model_adaptation/phase40_comparison_launch.py", "_SOURCE_PATHS", "preserve immutable source-closure member identity", "active"),
    ("archive-source-phase40-contract", "src/source_archiving/contracts.py", "src/model_adaptation/phase40_contract.py", "_SOURCE_PATHS", "preserve immutable source-closure member identity", "active"),
    ("archive-source-phase40-evidence", "src/source_archiving/contracts.py", "src/model_adaptation/phase40_evidence.py", "_SOURCE_PATHS", "preserve immutable source-closure member identity", "active"),
    ("archive-source-phase40-final-authority", "src/source_archiving/contracts.py", "src/model_adaptation/phase40_final_authority.py", "_SOURCE_PATHS", "preserve immutable source-closure member identity", "active"),
    ("archive-source-phase40-gguf", "src/source_archiving/contracts.py", "src/model_adaptation/phase40_gguf.py", "_SOURCE_PATHS", "preserve immutable source-closure member identity", "active"),
    ("archive-source-phase40-graphs", "src/source_archiving/contracts.py", "src/model_adaptation/phase40_graphs.py", "_SOURCE_PATHS", "preserve immutable source-closure member identity", "active"),
    ("archive-source-phase40-handoff", "src/source_archiving/contracts.py", "src/model_adaptation/phase40_handoff.py", "_SOURCE_PATHS", "preserve immutable source-closure member identity", "active"),
    ("archive-source-phase40-metrics", "src/source_archiving/contracts.py", "src/model_adaptation/phase40_metrics.py", "_SOURCE_PATHS", "preserve immutable source-closure member identity", "active"),
    ("archive-source-phase40-modes", "src/source_archiving/contracts.py", "src/model_adaptation/phase40_modes.py", "_SOURCE_PATHS", "preserve immutable source-closure member identity", "active"),
    ("archive-source-phase40-notebooks", "src/source_archiving/contracts.py", "src/model_adaptation/phase40_notebooks.py", "_SOURCE_PATHS", "preserve immutable source-closure member identity", "active"),
    ("archive-source-phase40-phobert-release", "src/source_archiving/contracts.py", "src/model_adaptation/phase40_phobert_release.py", "_SOURCE_PATHS", "preserve immutable source-closure member identity", "active"),
    ("archive-source-phase40-production-authorities", "src/source_archiving/contracts.py", "src/model_adaptation/phase40_production_authorities.py", "_SOURCE_PATHS", "preserve immutable source-closure member identity", "active"),
    ("archive-source-phase40-release-authorities", "src/source_archiving/contracts.py", "src/model_adaptation/phase40_release_authorities.py", "_SOURCE_PATHS", "preserve immutable source-closure member identity", "active"),
    ("archive-source-phase40-review", "src/source_archiving/contracts.py", "src/model_adaptation/phase40_review.py", "_SOURCE_PATHS", "preserve immutable source-closure member identity", "active"),
    ("archive-source-phase40-runtime-materialize", "src/source_archiving/contracts.py", "src/model_adaptation/phase40_runtime_materialize.py", "_SOURCE_PATHS", "preserve immutable source-closure member identity", "active"),
    ("archive-source-phase41-evaluation", "src/source_archiving/contracts.py", "src/model_adaptation/phase41_evaluation.py", "SOURCE_PHASE41_EVALUATION", "preserve immutable source-closure member identity", "active"),
    ("archive-source-phase41-protocols", "src/source_archiving/contracts.py", "src/model_adaptation/phase41_protocols.py", "_SOURCE_PATHS", "preserve immutable source-closure member identity", "active"),
    ("archive-production-evidence-root", "src/source_archiving/service.py", r"C:\ProgramData\VNPhish\phase41-evaluation-evidence", "PRODUCTION_EVIDENCE_ROOT", "preserve immutable production evidence authority identity", "active"),
    ("archive-production-manifest-root", "src/source_archiving/service.py", "data/models/phase41/verified-export", "PRODUCTION_MANIFEST_PATH", "preserve immutable verified-export manifest root", "active"),
    ("archive-production-destination-root", "src/source_archiving/service.py", "historical/phase41-source-closure", "PRODUCTION_DESTINATION", "preserve immutable archive destination root", "active"),
    ("archive-launcher-relative-path", "src/source_archiving/contracts.py", "scripts/phase41_one_shot_launcher.ps1", "LAUNCHER_RELATIVE_PATH", "preserve immutable launcher manifest identity", "active"),
)


@pytest.fixture(autouse=True)
def _register_windows_bound_descriptors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Expose synthetic BoundParent descriptors to the startup deny-open guard."""

    if os.name != "nt":
        return
    import msvcrt
    import sitecustomize

    implementation = msvcrt.open_osfhandle

    def registered(handle: int, flags: int) -> int:
        descriptor = implementation(handle, flags)
        sitecustomize._register_descriptor(descriptor)
        return descriptor

    monkeypatch.setattr(msvcrt, "open_osfhandle", registered)


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


def _owner_rows(document: dict[str, Any]) -> tuple[tuple[str, ...], ...]:
    fields = ("id", "path", "literal", "owner_symbol", "reason", "lifecycle")
    return tuple(tuple(str(row[field]) for field in fields) for row in document["frozen_literal_owners"])


def _synthetic_layout(tmp_path: Path) -> tuple[archive._ArchiveLayout, dict[str, bytes], bytes, bytes]:
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
            "path": r"C:\synthetic\pwsh.exe",
            "sha256": "2" * 64,
        },
        "preparation_scope": "synthetic",
        "python": {
            "bytes": 1,
            "path": r"C:\synthetic\python.exe",
            "runtime_import_roots": [r"C:\synthetic\site-packages"],
            "sha256": "3" * 64,
            "version": "3.13.13",
        },
        "schema_version": "phase41-execution-source-manifest-v1",
        "source_tree_sha256": "a" * 64,
        "upstream_declared_source_tree_sha256": "b" * 64,
    }
    manifest_raw = _canonical_json(manifest)
    manifest_path.parent.mkdir(parents=True)
    manifest_path.write_bytes(manifest_raw)
    destination.parent.mkdir(parents=True)
    repo_root = tmp_path / "current-repo"
    for relative, raw in members.items():
        path = repo_root / PurePosixPath(relative)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
    changed = b"changed\n"
    (repo_root / "src" / "example.py").write_bytes(changed)
    layout = archive._ArchiveLayout(
        manifest_path=manifest_path,
        evidence_root=evidence_root,
        source_root=source_root,
        launcher_path=launcher_path,
        destination=destination,
        repo_root=repo_root,
        expected_manifest_sha256=_sha256(manifest_raw),
        expected_schema_version="phase41-execution-source-manifest-v1",
        expected_tree_sha256="a" * 64,
        expected_launcher_sha256=_sha256(launcher),
        expected_source_paths=tuple(item["path"] for item in files),
        expected_worktree_mismatches=("src/example.py",),
    )
    return layout, members, launcher, changed


def _absolute_text(path: Path) -> str:
    return os.fspath(Path(os.path.abspath(os.path.normpath(os.fspath(path)))))


def test_archive_bytes_and_cli_streams_match_independent_pre_refactor_baseline(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    active = _strict_json(ACTIVE_TEXT_FIXTURE.read_bytes())
    tools = _strict_json(TOOL_FIXTURE.read_bytes())
    archive_tool = next(row for row in tools["tools"] if row["path"] == PRE_ARCHIVE_TOOL["path"])
    assert tools["contract_state"] == "pre_extraction_v1"
    assert archive_tool == PRE_ARCHIVE_TOOL
    assert {**PRE_ARCHIVE_TOOL, "imports": POST_ARCHIVE_TOOL["imports"]} == POST_ARCHIVE_TOOL
    assert active["contract_state"] == "pre_extraction_v1"
    assert _owner_rows(active) == PRE_ACTIVE_OWNERS
    assert len(PRE_ACTIVE_OWNERS) == 34
    assert len(POST_ACTIVE_OWNERS) == 31
    assert len({row[0] for row in PRE_ACTIVE_OWNERS}) == 34
    assert len({row[0] for row in POST_ACTIVE_OWNERS}) == 31
    assert {row[0] for row in PRE_ACTIVE_OWNERS} - {row[0] for row in POST_ACTIVE_OWNERS} == {
        "archive-facade-description",
        "archive-worktree-phase41-evaluation",
        "archive-production-launcher-filename",
    }

    assert archive.EXPECTED_SCHEMA_VERSION == "phase41-execution-source-manifest-v1"
    assert archive.EXPECTED_TREE_SHA256 == "c3bbc8c8adaf7579fd2eb9c59a0081613be4b2cae05dfdb64472938c7e6d0434"
    assert archive.EXPECTED_LAUNCHER_SHA256 == "c5f15a32b2c8d8ee196e3ec484707c27c4c05e5389d958626e775e44f52d49e9"
    assert archive.EXPECTED_MANIFEST_SHA256 == "41a3a7e166dd5077b3b2c689868b862bd5665137e1824094eb5ff1cdce2b0c61"
    assert archive.PROVENANCE_LABEL == "post_evaluation_archival_mirror_not_refactored_metric_producer"
    assert archive.RECEIPT_SCHEMA_VERSION == "phase411-source-closure-archival-receipt-v1"
    assert archive._WINDOWS_REPARSE_POINT == 0x00000400
    assert archive._SHA256_RE.pattern == r"^[0-9a-f]{64}$"
    assert archive._SOURCE_PATHS == EXPECTED_SOURCE_PATHS
    assert archive._WORKTREE_MISMATCHES == (
        "src/model_adaptation/cli.py",
        "src/model_adaptation/phase41_evaluation.py",
    )

    class FixedDateTime:
        @classmethod
        def now(cls, tz: timezone) -> datetime:
            assert tz is timezone.utc
            return datetime(2030, 1, 2, 3, 4, 5, tzinfo=timezone.utc)

        @classmethod
        def strptime(cls, value: str, pattern: str) -> datetime:
            return datetime.strptime(value, pattern)

    monkeypatch.setattr(archive, "datetime", FixedDateTime)
    monkeypatch.setattr(archive.secrets, "token_hex", lambda size: "0" * (size * 2))
    layout, members, launcher, changed = _synthetic_layout(tmp_path)
    manifest_raw = layout.manifest_path.read_bytes()
    receipt = archive._archive_bound_source_closure_for_test(layout)
    mismatch = {
        "actual_sha256": _sha256(changed),
        "expected_sha256": _sha256(members["src/example.py"]),
        "path": "src/example.py",
    }
    unsigned = {
        "archive_destination": _absolute_text(layout.destination),
        "archived_at_utc": "2030-01-02T03:04:05Z",
        "clean_runtime_origin": _absolute_text(layout.source_root),
        "current_worktree_mismatches": [mismatch],
        "file_count": 2,
        "launcher_origin": _absolute_text(layout.launcher_path),
        "launcher_sha256": _sha256(launcher),
        "manifest_sha256": _sha256(manifest_raw),
        "payload_file_count": 3,
        "provenance_label": "post_evaluation_archival_mirror_not_refactored_metric_producer",
        "schema_version": "phase411-source-closure-archival-receipt-v1",
        "source_manifest_origin": _absolute_text(layout.manifest_path),
        "source_tree_sha256": "a" * 64,
    }
    expected_receipt = {**unsigned, "receipt_sha256": _sha256(_canonical_json(unsigned))}
    assert receipt.as_dict() == expected_receipt
    assert (layout.destination / "execution-source-manifest.json").read_bytes() == manifest_raw
    assert (layout.destination / "tree/src/__init__.py").read_bytes() == members["src/__init__.py"]
    assert (layout.destination / "tree/src/example.py").read_bytes() == members["src/example.py"]
    assert (layout.destination / "tree/scripts/phase41_one_shot_launcher.ps1").read_bytes() == launcher
    receipt_raw = (layout.destination / "archival-receipt.json").read_bytes()
    assert receipt_raw == _canonical_json(expected_receipt)
    assert _sha256(receipt_raw) == _sha256(_canonical_json(expected_receipt))

    class SyntheticReceipt:
        def __init__(self, selected: str) -> None:
            self.selected = selected

        def as_dict(self) -> dict[str, str]:
            return {"selected": self.selected}

    calls = {"archive": 0, "verify": 0}

    def selected_archive() -> SyntheticReceipt:
        calls["archive"] += 1
        return SyntheticReceipt("archive")

    def selected_verify() -> SyntheticReceipt:
        calls["verify"] += 1
        return SyntheticReceipt("verify")

    monkeypatch.setattr(archive, "archive_bound_source_closure", selected_archive)
    monkeypatch.setattr(archive, "verify_archived_source_closure", selected_verify)
    for command in ("archive", "verify"):
        before = dict(calls)
        assert archive.main([command]) == 0
        captured = capsys.readouterr()
        assert captured.out == f'{{"selected":"{command}"}}\n'
        assert captured.err == ""
        assert calls[command] == before[command] + 1
        other = "verify" if command == "archive" else "archive"
        assert calls[other] == before[other]

    monkeypatch.setattr(archive.sys, "argv", ["archive-tool"])
    before = dict(calls)
    with pytest.raises(SystemExit) as missing:
        archive.main([])
    captured = capsys.readouterr()
    assert missing.value.code == 2
    assert captured.out == ""
    assert captured.err == (
        "usage: archive-tool [-h] {archive,verify}\n"
        "archive-tool: error: the following arguments are required: command\n"
    )
    assert calls == before
    with pytest.raises(SystemExit) as invalid:
        archive.main(["invalid"])
    captured = capsys.readouterr()
    assert invalid.value.code == 2
    assert captured.out == ""
    assert captured.err == (
        "usage: archive-tool [-h] {archive,verify}\n"
        "archive-tool: error: argument command: invalid choice: 'invalid' "
        "(choose from archive, verify)\n"
    )
    assert calls == before


def test_archive_facade_help_uses_exact_domain_language(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert archive.__doc__ == "Archive and verify an immutable source closure for reproducible evidence."
    monkeypatch.setattr(archive.sys, "argv", ["archive-tool"])
    with pytest.raises(SystemExit) as help_exit:
        archive.main(["--help"])
    captured = capsys.readouterr()
    assert help_exit.value.code == 0
    assert captured.err == ""
    assert captured.out == (
        "usage: archive-tool [-h] {archive,verify}\n\n"
        "Archive and verify an immutable source closure for reproducible evidence.\n\n"
        "positional arguments:\n"
        "  {archive,verify}  archive a source closure or verify an existing archive\n\n"
        "options:\n"
        "  -h, --help        show this help message and exit\n"
    )
