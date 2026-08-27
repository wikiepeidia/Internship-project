"""Fixture-only authority, retention, and report-handoff truth gates."""

from __future__ import annotations

import copy
import math
import ntpath
import os
from pathlib import Path
import re
from typing import Any, Iterator

import pytest

from tests.architecture.json_contract import (
    load_strict_json as _load_json,
    strict_json as _strict_json,
)


REPO_ROOT = Path(__file__).parents[2]
FACT_PATH = REPO_ROOT / "tests/architecture/fixtures/report_fact_contract.json"
BASELINE_PATH = REPO_ROOT / "tests/architecture/fixtures/protected_authority_baseline.json"
INVENTORY_PATH = REPO_ROOT / ".planning/phases/41.1-codebase-architecture-overhaul/41.1-STORAGE-INVENTORY.md"
PROVENANCE_PATH = REPO_ROOT / "docs/architecture/provenance.md"
STORAGE_PATH = REPO_ROOT / "docs/architecture/storage-retention.md"
OVERVIEW_PATH = REPO_ROOT / "docs/architecture/overview.md"
POLICY_PATH = REPO_ROOT / "architecture/module-boundaries.json"
HANDOFF_PATH = REPO_ROOT / ".planning/phases/41.1-codebase-architecture-overhaul/41.1-REPORT-HANDOFF.md"

SOURCE_TREE = "c3bbc8c8adaf7579fd2eb9c59a0081613be4b2cae05dfdb64472938c7e6d0434"
EXPORT_IDENTITY = "9ac54d58c273ab0a8c2f2b4b61e472a51ca94231a94b6847637ecad6ceee49f7"
RECEIPT_SHA256 = "ca4ca1bf019b567d5bfa2380658a11245d76543b323ce5e2fcf6cfe3f525213a"
SOURCE_MANIFEST_SHA256 = "41a3a7e166dd5077b3b2c689868b862bd5665137e1824094eb5ff1cdce2b0c61"
LAUNCHER_SHA256 = "c5f15a32b2c8d8ee196e3ec484707c27c4c05e5389d958626e775e44f52d49e9"
ERRATUM_SHA256 = "c7be74346f0e217c382e556fbf0a730cb33be50356d4155356a5b024871a1672"
PROVENANCE_LABEL = "post_evaluation_archival_mirror_not_refactored_metric_producer"
CORRECTED_CLAIM = (
    "Phase 41 contains exactly one terminal shared-cohort model-evaluation pass over "
    "the frozen Qwen QLoRA and PhoBERT models. It does not have zero prior filesystem "
    "access to the held-out file."
)
SOURCE_RECEIPT_RELATIVE = f"historical/phase41-source-closure/{SOURCE_TREE}/archival-receipt.json"
EXPORT_MANIFEST_RELATIVE = f"data/models/phase41/verified-export/{EXPORT_IDENTITY}/evidence-manifest.json"
ERRATUM_RELATIVE = "data/models/phase41/phase41-provenance-erratum.json"

PHASE_ROOT = r"D:\PROJEct\AI MODELS\phase40-full-local-20260825"
SEALED_ROOTS = [
    ("Qwen QLoRA adapter", PHASE_ROOT + r"\transfer-root-v3\data\models\phase40\full\qwen-qlora\adapter-or-model", "0.139 GiB", "466d107d7212fd9b65f19b36be5011e6043865bce4c937460145908d3847b7ec"),
    ("Qwen base", PHASE_ROOT + r"\transfer-root-v3\data\models\phase40\base\qwen3-4b-instruct-2507", "7.507 GiB", "bab9c18a02587fb842c9332848bdc4f1316bae7ee5bed3bb1d573dca2d64554c"),
    ("PhoBERT inference bundle", PHASE_ROOT + r"\phobert-release-v4\data\models\phase40\inference\phobert", "1.513 GiB", "649f566a6525833778fbc617261278ef53e4ecc6ab88ae54715f6aaf7b56bb7a"),
    ("PhoBERT base", PHASE_ROOT + r"\transfer-root-v5\data\models\phase40\base\phobert-base-v2", "1.011 GiB", "1708ec099dcc8385a88ab49d0bb7860e4ceb496fd08aa792b0ec95e2326d8d5f"),
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
    (PHASE_ROOT + r"\transfer-root-v3\data\models\phase40\base\phobert-base-v2", "1.011 GiB"),
    (PHASE_ROOT + r"\transfer-root-v5\data\models\phase40\full\phobert", "1.514 GiB"),
    (PHASE_ROOT + r"\phobert-release-v4\data\models\phase40\full\phobert", "1.514 GiB"),
]
OLDER_BASES = [
    (r"D:\PROJEct\AI MODELS\base\qwen2.5-7b-instruct", "14.196 GiB"),
    (r"D:\PROJEct\AI MODELS\base\qwen3.5-4b", "8.701 GiB"),
]

DESTRUCTIVE_HEAD = re.compile(
    r"(?i)^(?:rm\b|rmdir\b|rd(?:\.exe)?\s+/|del(?:\.exe)?\s+/|erase\b|Remove-Item\b|shutil\.rmtree\b)"
)
SECRET_VALUE = re.compile(
    r"(?ix)(?:\b(?:sk-[A-Za-z0-9_-]{8,}|ghp_[A-Za-z0-9]{8,}|github_pat_[A-Za-z0-9_]{8,}|hf_[A-Za-z0-9]{8,})\b|"
    r"(?:\$env:)?\b(?:api[_-]?key|access[_-]?token|secret|password)\b\s*(?:=|:)\s*[\"']?"
    r"(?!<redacted>|redacted\b|x{4,}\b|\*{4,}\b)[A-Za-z0-9_./+=-]{8,})"
)
BANNED_OVERCLAIMS = (
    "zero prior filesystem access", "the only process that ever opened",
    "untouched until the launcher", "the refactored code produced the frozen metrics",
    "cleanup has been authorized", "one model is superior",
)


def _validate_fact_contract(facts: dict[str, Any]) -> None:
    assert list(facts) == ["erratum", "export", "schema_version", "source"]
    assert facts["schema_version"] == "phase411-report-fact-contract-v1"
    erratum = facts["erratum"]
    export = facts["export"]
    source = facts["source"]
    assert isinstance(erratum, dict) and list(erratum) == [
        "corrected_claim", "path", "schema_version",
        "sealed_export_evidence_manifest_sha256", "sha256",
    ]
    assert isinstance(export, dict) and list(export) == [
        "artifact_count", "evidence_manifest_sha256", "manifest_path",
        "schema_version", "terminal_policy",
    ]
    assert isinstance(source, dict) and list(source) == [
        "archival_receipt_sha256", "execution_source_manifest_sha256", "launcher_sha256",
        "provenance_label", "receipt_path", "source_tree_sha256",
    ]
    assert erratum == {
        "corrected_claim": CORRECTED_CLAIM,
        "path": ERRATUM_RELATIVE,
        "schema_version": "phase41-provenance-erratum-v1",
        "sealed_export_evidence_manifest_sha256": EXPORT_IDENTITY,
        "sha256": ERRATUM_SHA256,
    }
    assert export == {
        "artifact_count": 12,
        "evidence_manifest_sha256": EXPORT_IDENTITY,
        "manifest_path": EXPORT_MANIFEST_RELATIVE,
        "schema_version": "phase41-evidence-manifest-v1",
        "terminal_policy": {
            "rerun_permitted": False,
            "test_outcome_used_for_tuning": False,
            "unbiased_test_score_claim_after_deployment_fit": False,
        },
    }
    assert source == {
        "archival_receipt_sha256": RECEIPT_SHA256,
        "execution_source_manifest_sha256": SOURCE_MANIFEST_SHA256,
        "launcher_sha256": LAUNCHER_SHA256,
        "provenance_label": PROVENANCE_LABEL,
        "receipt_path": SOURCE_RECEIPT_RELATIVE,
        "source_tree_sha256": SOURCE_TREE,
    }
    assert type(export["artifact_count"]) is int
    assert all(type(value) is bool for value in export["terminal_policy"].values())
    assert all(math.isfinite(value) for value in [float(export["artifact_count"])])


def _marked_table(document: str, name: str, width: int) -> list[tuple[str, ...]]:
    start = f"<!-- {name}:start -->"
    end = f"<!-- {name}:end -->"
    assert document.count(start) == document.count(end) == 1
    block = document.split(start, 1)[1].split(end, 1)[0]
    rows = [line.strip() for line in block.splitlines() if line.strip().startswith("|")]
    parsed = [tuple(cell.strip() for cell in row.strip("|").split("|")) for row in rows]
    assert len(parsed) >= 2 and all(len(row) == width for row in parsed)
    assert all(set(cell) <= {"-", ":", " "} for cell in parsed[1])
    return [tuple(_unquote(cell) for cell in row) for row in parsed[2:]]


def _unquote(value: str) -> str:
    assert value.startswith("`") and value.endswith("`")
    return value[1:-1]


def _allowed_hashes(facts: dict[str, Any]) -> set[str]:
    return {
        facts["source"]["source_tree_sha256"],
        facts["source"]["archival_receipt_sha256"],
        facts["source"]["execution_source_manifest_sha256"],
        facts["source"]["launcher_sha256"],
        facts["export"]["evidence_manifest_sha256"],
        facts["erratum"]["sha256"],
        *(row[3] for row in SEALED_ROOTS), OPTIONAL_GGUF[3],
    }


def _command_segments(document: str) -> Iterator[str]:
    presentation = re.compile(
        r"(?i)^(?:>\s*|[-*+]\s+|\d+[.)]\s+|\[[ x]\]\s+)+"
    )
    prompts = (
        re.compile(r"^\$\s+"),
        re.compile(r"(?i)^PS\s+[^>]*>\s*"),
        re.compile(r"(?i)^[A-Z]:\\[^>]*>\s*"),
    )
    wrappers = (
        re.compile(r"(?i)^cmd(?:\.exe)?\s+/[cs]\s+"),
        re.compile(r"(?i)^(?:powershell|powershell\.exe|pwsh|pwsh\.exe)\b.*?\s-Command\s+"),
        re.compile(r"(?i)^(?:sh|bash)\s+-c\s+"),
    )
    for raw_line in document.splitlines():
        line = raw_line.strip()
        previous = None
        while line and line != previous:
            previous = line
            line = presentation.sub("", line).strip()
            for prompt in prompts:
                line = prompt.sub("", line).strip()
            line = line.strip("`\"'").strip()
            for wrapper in wrappers:
                line = wrapper.sub("", line).strip().strip("`\"'").strip()
        for segment in re.split(r"\s*(?:&&|\|\||;)\s*", line):
            if segment:
                yield segment


def _assert_safe_static_text(document: str) -> None:
    assert not any(DESTRUCTIVE_HEAD.search(segment) for segment in _command_segments(document))
    assert not SECRET_VALUE.search(document)
    lowered = document.lower().replace(
        "does not have zero prior filesystem access", "records prior filesystem access"
    )
    assert all(claim not in lowered for claim in BANNED_OVERCLAIMS)
    assert "data/splits" not in lowered and "test.jsonl" not in lowered


def _validate_provenance(document: str, facts: dict[str, Any]) -> None:
    _validate_fact_contract(facts)
    _assert_safe_static_text(document)
    source, export, erratum = facts["source"], facts["export"], facts["erratum"]
    for value in (
        source["source_tree_sha256"], source["archival_receipt_sha256"],
        source["execution_source_manifest_sha256"], source["launcher_sha256"],
        source["provenance_label"], export["evidence_manifest_sha256"],
        export["schema_version"], erratum["sha256"], erratum["corrected_claim"],
    ):
        assert str(value) in document
    assert "reports\nstatus `completed`, and names 12 hash-bound members" in document
    assert "Current source is not the metric-producing source" in document
    assert "Every downstream result claim must cite the verified export and the erratum together." in document
    hashes = set(re.findall(r"\b[0-9a-f]{64}\b", document))
    required = {
        source["source_tree_sha256"], source["archival_receipt_sha256"],
        source["execution_source_manifest_sha256"], source["launcher_sha256"],
        export["evidence_manifest_sha256"], erratum["sha256"],
    }
    assert required <= hashes <= _allowed_hashes(facts)


def _validate_storage(document: str) -> None:
    _assert_safe_static_text(document)
    assert _marked_table(document, "sealed-roots", 4) == SEALED_ROOTS
    assert _marked_table(document, "optional-gguf", 4) == [OPTIONAL_GGUF]
    assert _marked_table(document, "cleanup-candidates", 3) == CLEANUP_CANDIDATES
    assert _marked_table(document, "nested-candidates", 2) == NESTED_CANDIDATES
    assert _marked_table(document, "older-bases", 2) == OLDER_BASES
    assert all(value in document for value in (
        "10.170 GiB", "30.304 GiB", "4.040 GiB",
        "informational and not authorized for deletion",
        "separate exact-path user authorization", "NTFS hardlinks",
    ))
    assert set(re.findall(r"\b[0-9a-f]{64}\b", document)) == {
        *(row[3] for row in SEALED_ROOTS), OPTIONAL_GGUF[3]
    }


def _validate_handoff(document: str, facts: dict[str, Any]) -> None:
    _validate_fact_contract(facts)
    _assert_safe_static_text(document)
    for heading in (
        "## Architecture facts", "## Metric-authority facts",
        "## Required limitation language", "## Prohibited claims",
        "## Source citations", "## Later-phase ownership",
    ):
        assert heading in document
    required = (
        "The refactored code did not generate the frozen metrics.",
        "At least two broad default pytest executions before the terminal model evaluation parsed, statted, and hashed the live split files; the exact count may be higher.",
        "One focused post-evaluation regression rerun also reread the live split files.",
        "No terminal model-evaluation retry occurred.",
        "The test outcome was not used for tuning, model selection, thresholding, retraining, or dataset repair.",
        "Every result claim must cite the verified export and mandatory erratum together.",
        "Phase 44—not this handoff—owns student-written comments and the guided defense walkthrough.",
    )
    assert all(statement in document for statement in required)
    for value in (
        facts["source"]["source_tree_sha256"], facts["source"]["provenance_label"],
        facts["export"]["evidence_manifest_sha256"], facts["erratum"]["sha256"],
        facts["erratum"]["corrected_claim"],
    ):
        assert value in document
    assert set(re.findall(r"\b[0-9a-f]{64}\b", document)) <= _allowed_hashes(facts)


def _leaf_paths(value: object, prefix: tuple[object, ...] = ()) -> Iterator[tuple[object, ...]]:
    if isinstance(value, dict):
        for key, child in value.items():
            yield from _leaf_paths(child, (*prefix, key))
    else:
        yield prefix


def _mutate_leaf(document: dict[str, Any], path: tuple[object, ...]) -> None:
    owner: Any = document
    for key in path[:-1]:
        owner = owner[key]
    key = path[-1]
    value = owner[key]
    if type(value) is bool:
        owner[key] = not value
    elif type(value) is int:
        owner[key] = value + 1
    else:
        owner[key] = str(value) + "-mutated"


def test_report_fact_fixture_is_strict_and_baseline_bound() -> None:
    facts = _load_json(FACT_PATH)
    _validate_fact_contract(facts)
    baseline = _load_json(BASELINE_PATH)
    authorities = {item["path"]: item for item in baseline["protected_authorities"]}
    source_manifest_path = f"data/models/phase41/verified-export/{EXPORT_IDENTITY}/execution-source-manifest.json"
    assert authorities[source_manifest_path]["worktree_sha256"] == facts["source"]["execution_source_manifest_sha256"]
    assert authorities[ERRATUM_RELATIVE]["worktree_sha256"] == facts["erratum"]["sha256"]
    assert facts["erratum"]["sealed_export_evidence_manifest_sha256"] == facts["export"]["evidence_manifest_sha256"]
    raw = FACT_PATH.read_bytes()
    with pytest.raises(AssertionError, match="duplicate JSON key"):
        _strict_json(b'{"schema_version":"duplicate",' + raw[1:])
    with pytest.raises(AssertionError, match="non-finite"):
        _strict_json(b'{"value":NaN}')


def test_provenance_binds_source_export_and_erratum() -> None:
    _validate_provenance(PROVENANCE_PATH.read_text(encoding="utf-8"), _load_json(FACT_PATH))


def test_storage_retention_matches_approved_inventory_without_deletion() -> None:
    assert "nothing deleted" in INVENTORY_PATH.read_text(encoding="utf-8").lower()
    _validate_storage(STORAGE_PATH.read_text(encoding="utf-8"))


def test_report_handoff_carries_facts_limitations_and_later_phase_scope() -> None:
    _validate_handoff(HANDOFF_PATH.read_text(encoding="utf-8"), _load_json(FACT_PATH))


def test_handoff_historical_cycle_count_matches_policy() -> None:
    policy = _load_json(POLICY_PATH)
    assert policy["schema_version"] == "module-boundaries-v2"
    assert len(policy["historical_sccs"]) == 4
    overview = OVERVIEW_PATH.read_text(encoding="utf-8")
    block = overview.split("<!-- historical-sccs:start -->", 1)[1].split("<!-- historical-sccs:end -->", 1)[0]
    rows = [line for line in block.splitlines() if line.lstrip().startswith("|")]
    assert len(rows) - 2 == 4
    assert "four reviewed legacy-only cycles" in HANDOFF_PATH.read_text(encoding="utf-8")


def test_static_validators_reject_missing_authority_invented_facts_and_commands() -> None:
    facts = _load_json(FACT_PATH)
    for path in _leaf_paths(facts):
        mutated = copy.deepcopy(facts)
        _mutate_leaf(mutated, path)
        with pytest.raises(AssertionError):
            _validate_fact_contract(mutated)
    provenance = PROVENANCE_PATH.read_text(encoding="utf-8")
    storage = STORAGE_PATH.read_text(encoding="utf-8")
    handoff = HANDOFF_PATH.read_text(encoding="utf-8")
    with pytest.raises(AssertionError):
        _validate_provenance(provenance.replace(ERRATUM_SHA256, "f" * 64), facts)
    with pytest.raises(AssertionError):
        _validate_storage(storage.replace("10.170 GiB", "10.999 GiB"))
    with pytest.raises(AssertionError):
        _validate_storage(storage + "\nRemove-Item -Recurse candidate\n")
    with pytest.raises(AssertionError):
        _validate_handoff(handoff + "\nThe held-out file had zero prior filesystem access.\n", facts)

    destructive_mutations = (
        "- rm -rf candidate",
        "> Remove-Item -Recurse candidate",
        "$ del /q candidate",
        r"PS C:\repo> rd /s /q candidate",
        "- cmd /c del /q candidate",
        "> PowerShell -Command Remove-Item -Recurse candidate",
        "1. sh -c 'rm -rf candidate'",
    )
    secret_mutations = (
        "api_key: actualvalue123",
        "$env:ACCESS_TOKEN=actualvalue123",
        "token=sk-abcdefgh1234",
        "token=ghp_abcdefgh1234",
        "token=github_pat_abcdefgh1234",
        "token=hf_abcdefgh1234",
    )
    for mutation in (*destructive_mutations, *secret_mutations):
        with pytest.raises(AssertionError):
            _assert_safe_static_text(storage + "\n" + mutation + "\n")
    for redacted in ("api_key=<redacted>", "access_token=********"):
        _assert_safe_static_text(storage + "\n" + redacted + "\n")


def test_former_live_authority_paths_are_guarded_before_call() -> None:
    import sitecustomize

    calls = {"underlying": 0}

    def recorder(*_args: object, **_kwargs: object) -> None:
        calls["underlying"] += 1

    guarded = sitecustomize._make_path_guard("synthetic.authority-read", recorder)
    for relative in (SOURCE_RECEIPT_RELATIVE, EXPORT_MANIFEST_RELATIVE, ERRATUM_RELATIVE):
        lexical = ntpath.join(os.fspath(REPO_ROOT), relative.replace("/", "\\"))
        with pytest.raises(PermissionError, match="forbidden authority path"):
            guarded(lexical)
    assert calls == {"underlying": 0}
