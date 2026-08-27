"""Static authority, retention, and report-handoff truth gates."""

from __future__ import annotations

import json
from pathlib import Path
import re
from typing import Any

import pytest


REPO_ROOT = Path(__file__).parents[2]
SOURCE_TREE = "c3bbc8c8adaf7579fd2eb9c59a0081613be4b2cae05dfdb64472938c7e6d0434"
EXPORT_IDENTITY = "9ac54d58c273ab0a8c2f2b4b61e472a51ca94231a94b6847637ecad6ceee49f7"
SOURCE_RECEIPT_PATH = (
    REPO_ROOT
    / "historical/phase41-source-closure"
    / SOURCE_TREE
    / "archival-receipt.json"
)
EXPORT_MANIFEST_PATH = (
    REPO_ROOT
    / "data/models/phase41/verified-export"
    / EXPORT_IDENTITY
    / "evidence-manifest.json"
)
ERRATUM_PATH = REPO_ROOT / "data/models/phase41/phase41-provenance-erratum.json"
BASELINE_PATH = REPO_ROOT / "tests/architecture/fixtures/protected_authority_baseline.json"
INVENTORY_PATH = (
    REPO_ROOT
    / ".planning/phases/41.1-codebase-architecture-overhaul/41.1-STORAGE-INVENTORY.md"
)
PROVENANCE_PATH = REPO_ROOT / "docs/architecture/provenance.md"
STORAGE_PATH = REPO_ROOT / "docs/architecture/storage-retention.md"
HANDOFF_PATH = (
    REPO_ROOT
    / ".planning/phases/41.1-codebase-architecture-overhaul/41.1-REPORT-HANDOFF.md"
)
PHASE_ROOT = r"D:\PROJEct\AI MODELS\phase40-full-local-20260825"
SEALED_ROOTS = [
    (
        "Qwen QLoRA adapter",
        PHASE_ROOT + r"\transfer-root-v3\data\models\phase40\full\qwen-qlora\adapter-or-model",
        "0.139 GiB",
        "466d107d7212fd9b65f19b36be5011e6043865bce4c937460145908d3847b7ec",
    ),
    (
        "Qwen base",
        PHASE_ROOT + r"\transfer-root-v3\data\models\phase40\base\qwen3-4b-instruct-2507",
        "7.507 GiB",
        "bab9c18a02587fb842c9332848bdc4f1316bae7ee5bed3bb1d573dca2d64554c",
    ),
    (
        "PhoBERT inference bundle",
        PHASE_ROOT + r"\phobert-release-v4\data\models\phase40\inference\phobert",
        "1.513 GiB",
        "649f566a6525833778fbc617261278ef53e4ecc6ab88ae54715f6aaf7b56bb7a",
    ),
    (
        "PhoBERT base",
        PHASE_ROOT + r"\transfer-root-v5\data\models\phase40\base\phobert-base-v2",
        "1.011 GiB",
        "1708ec099dcc8385a88ab49d0bb7860e4ceb496fd08aa792b0ec95e2326d8d5f",
    ),
]
OPTIONAL_GGUF = (
    "Qwen Q8_0 GGUF and manifest",
    PHASE_ROOT + r"\exports-v3\qwen-qlora-q8_0.gguf",
    "3.986 GiB",
    "457f6f92d36a7d54da9916fd80a4028dcd055a653a015c4877370a0fea4d18ab",
)
CLEANUP_CANDIDATES = [
    (PHASE_ROOT + r"\phobert-work-v12", "14.103 GiB", "trainer checkpoints and final-model staging"),
    (PHASE_ROOT + r"\work-v3", "4.122 GiB", "Qwen checkpoints and intermediate adapters"),
    (PHASE_ROOT + r"\resume-work-v2", "1.008 GiB", "interrupted superseded Qwen attempt"),
    (PHASE_ROOT + r"\phobert-release-v2", "part of 6.058 GiB", "superseded by v4"),
    (PHASE_ROOT + r"\phobert-release-v3", "part of 6.058 GiB", "superseded by v4"),
    (PHASE_ROOT + r"\comparison-root-v4", "part of 5.013 GiB", "comparison staging"),
    (PHASE_ROOT + r"\comparison-root-v5", "part of 5.013 GiB", "comparison staging"),
    (PHASE_ROOT + r"\comparison-root-v6", "part of 5.013 GiB", "comparison staging"),
]
NESTED_CANDIDATES = [
    (
        PHASE_ROOT + r"\transfer-root-v3\data\models\phase40\base\phobert-base-v2",
        "1.011 GiB",
    ),
    (
        PHASE_ROOT + r"\transfer-root-v5\data\models\phase40\full\phobert",
        "1.514 GiB",
    ),
    (
        PHASE_ROOT + r"\phobert-release-v4\data\models\phase40\full\phobert",
        "1.514 GiB",
    ),
]
OLDER_BASES = [
    (r"D:\PROJEct\AI MODELS\base\qwen2.5-7b-instruct", "14.196 GiB"),
    (r"D:\PROJEct\AI MODELS\base\qwen3.5-4b", "8.701 GiB"),
]
DELETION_COMMAND = re.compile(
    r"(?im)^\s*(?:rm\b|rmdir\b|rd\s+/|del\s+/|erase\b|Remove-Item\b|shutil\.rmtree\b)"
)
SECRET_ASSIGNMENT = re.compile(
    r"(?i)(?:sk-[A-Za-z0-9]{8,}|\b(?:api[_-]?key|access[_-]?token|secret)\s*=)"
)
BANNED_OVERCLAIMS = (
    "zero prior filesystem access",
    "the only process that ever opened",
    "untouched until the launcher",
    "the refactored code produced the frozen metrics",
    "cleanup has been authorized",
    "one model is superior",
)


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


def _marked_table(document: str, name: str, width: int) -> list[tuple[str, ...]]:
    start = f"<!-- {name}:start -->"
    end = f"<!-- {name}:end -->"
    assert document.count(start) == document.count(end) == 1
    block = document.split(start, 1)[1].split(end, 1)[0]
    rows = [line.strip() for line in block.splitlines() if line.strip().startswith("|")]
    parsed = [tuple(cell.strip() for cell in row.strip("|").split("|")) for row in rows]
    assert len(parsed) >= 2
    assert all(len(row) == width for row in parsed)
    assert all(set(cell) <= {"-", ":", " "} for cell in parsed[1])
    return [tuple(_unquote(cell) for cell in row) for row in parsed[2:]]


def _unquote(value: str) -> str:
    assert value.startswith("`") and value.endswith("`")
    return value[1:-1]


def _erratum_sha(baseline: dict[str, Any]) -> str:
    matches = [
        row["worktree_sha256"]
        for row in baseline["protected_authorities"]
        if row["path"] == "data/models/phase41/phase41-provenance-erratum.json"
    ]
    assert len(matches) == 1
    return matches[0]


def _allowed_hashes(
    receipt: dict[str, Any], baseline: dict[str, Any]
) -> set[str]:
    return {
        SOURCE_TREE,
        EXPORT_IDENTITY,
        receipt["receipt_sha256"],
        receipt["manifest_sha256"],
        receipt["launcher_sha256"],
        _erratum_sha(baseline),
        *(row[3] for row in SEALED_ROOTS),
        OPTIONAL_GGUF[3],
    }


def _assert_safe_static_text(document: str) -> None:
    assert not DELETION_COMMAND.search(document)
    assert not SECRET_ASSIGNMENT.search(document)
    lowered = document.lower()
    assert all(claim not in lowered for claim in BANNED_OVERCLAIMS)
    assert "data/splits" not in lowered
    assert "test.jsonl" not in lowered


def _validate_provenance(
    document: str,
    receipt: dict[str, Any],
    manifest: dict[str, Any],
    erratum: dict[str, Any],
    baseline: dict[str, Any],
) -> None:
    _assert_safe_static_text(document)
    assert receipt["source_tree_sha256"] == SOURCE_TREE
    assert receipt["provenance_label"] in document
    assert receipt["source_tree_sha256"] in document
    assert receipt["receipt_sha256"] in document
    assert receipt["manifest_sha256"] in document
    assert receipt["launcher_sha256"] in document
    assert manifest["schema_version"] == "phase41-evidence-manifest-v1"
    assert len(manifest["artifacts"]) == 12
    assert manifest["terminal_policy"] == {
        "rerun_permitted": False,
        "test_outcome_used_for_tuning": False,
        "unbiased_test_score_claim_after_deployment_fit": False,
    }
    assert EXPORT_IDENTITY in document
    erratum_sha = _erratum_sha(baseline)
    assert erratum["schema_version"] == "phase41-provenance-erratum-v1"
    assert erratum["sealed_export"]["evidence_manifest_sha256"] == EXPORT_IDENTITY
    assert erratum_sha in document
    assert erratum["corrected_claim"] in document
    assert "active architecture" in document.lower()
    assert "historical producer source" in document.lower()
    assert "Current source is not the metric-producing source" in document
    assert "Every downstream result claim must cite the verified export and the erratum together." in document

    hashes = set(re.findall(r"\b[0-9a-f]{64}\b", document))
    required = {
        SOURCE_TREE,
        EXPORT_IDENTITY,
        receipt["receipt_sha256"],
        receipt["manifest_sha256"],
        receipt["launcher_sha256"],
        erratum_sha,
    }
    assert required <= hashes <= _allowed_hashes(receipt, baseline)


def _validate_storage(document: str) -> None:
    _assert_safe_static_text(document)
    assert _marked_table(document, "sealed-roots", 4) == SEALED_ROOTS
    assert _marked_table(document, "optional-gguf", 4) == [OPTIONAL_GGUF]
    assert _marked_table(document, "cleanup-candidates", 3) == CLEANUP_CANDIDATES
    assert _marked_table(document, "nested-candidates", 2) == NESTED_CANDIDATES
    assert _marked_table(document, "older-bases", 2) == OLDER_BASES
    assert "10.170 GiB" in document
    assert "30.304 GiB" in document
    assert "4.040 GiB" in document
    assert "informational and not authorized for deletion" in document
    assert "separate exact-path user authorization" in document
    assert "NTFS hardlinks" in document
    hashes = set(re.findall(r"\b[0-9a-f]{64}\b", document))
    assert hashes == {*(row[3] for row in SEALED_ROOTS), OPTIONAL_GGUF[3]}


def _validate_handoff(
    document: str,
    receipt: dict[str, Any],
    erratum: dict[str, Any],
    baseline: dict[str, Any],
) -> None:
    _assert_safe_static_text(document)
    for heading in (
        "## Architecture facts",
        "## Metric-authority facts",
        "## Required limitation language",
        "## Prohibited claims",
        "## Source citations",
        "## Later-phase ownership",
    ):
        assert heading in document
    required_statements = (
        "The refactored code did not generate the frozen metrics.",
        "At least two broad default pytest executions before the terminal model evaluation parsed, statted, and hashed the live split files; the exact count may be higher.",
        "One focused post-evaluation regression rerun also reread the live split files.",
        "No terminal model-evaluation retry occurred.",
        "The test outcome was not used for tuning, model selection, thresholding, retraining, or dataset repair.",
        "Every result claim must cite the verified export and mandatory erratum together.",
        "Phase 44—not this handoff—owns student-written comments and the guided defense walkthrough.",
    )
    assert all(statement in document for statement in required_statements)
    assert SOURCE_TREE in document
    assert EXPORT_IDENTITY in document
    assert _erratum_sha(baseline) in document
    assert receipt["provenance_label"] in document
    assert erratum["corrected_claim"] in document
    assert "current active architecture" in document.lower()
    assert "historical producer source" in document.lower()
    hashes = set(re.findall(r"\b[0-9a-f]{64}\b", document))
    assert hashes <= _allowed_hashes(receipt, baseline)


def test_provenance_binds_source_export_and_erratum() -> None:
    _validate_provenance(
        PROVENANCE_PATH.read_text(encoding="utf-8"),
        _load_json(SOURCE_RECEIPT_PATH),
        _load_json(EXPORT_MANIFEST_PATH),
        _load_json(ERRATUM_PATH),
        _load_json(BASELINE_PATH),
    )


def test_storage_retention_matches_approved_inventory_without_deletion() -> None:
    inventory = INVENTORY_PATH.read_text(encoding="utf-8")
    assert "nothing deleted" in inventory.lower()
    _validate_storage(STORAGE_PATH.read_text(encoding="utf-8"))


def test_report_handoff_carries_facts_limitations_and_later_phase_scope() -> None:
    _validate_handoff(
        HANDOFF_PATH.read_text(encoding="utf-8"),
        _load_json(SOURCE_RECEIPT_PATH),
        _load_json(ERRATUM_PATH),
        _load_json(BASELINE_PATH),
    )


def test_static_validators_reject_missing_authority_invented_facts_and_commands() -> None:
    receipt = _load_json(SOURCE_RECEIPT_PATH)
    manifest = _load_json(EXPORT_MANIFEST_PATH)
    erratum = _load_json(ERRATUM_PATH)
    baseline = _load_json(BASELINE_PATH)
    provenance = PROVENANCE_PATH.read_text(encoding="utf-8")
    storage = STORAGE_PATH.read_text(encoding="utf-8")
    handoff = HANDOFF_PATH.read_text(encoding="utf-8")

    with pytest.raises(AssertionError):
        _validate_provenance(
            provenance.replace(_erratum_sha(baseline), "f" * 64),
            receipt,
            manifest,
            erratum,
            baseline,
        )
    with pytest.raises(AssertionError):
        _validate_storage(storage.replace("10.170 GiB", "10.999 GiB"))
    with pytest.raises(AssertionError):
        _validate_storage(storage + "\nRemove-Item -Recurse candidate\n")
    with pytest.raises(AssertionError):
        _validate_handoff(
            handoff + "\nThe held-out file had zero prior filesystem access.\n",
            receipt,
            erratum,
            baseline,
        )
