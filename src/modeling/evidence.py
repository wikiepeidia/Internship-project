"""Read-only validation of a frozen export and its mandatory disclosure."""

from __future__ import annotations

from dataclasses import dataclass, field
import json
from pathlib import Path
from typing import Any, Literal, Mapping

from pydantic import ValidationError

from src.core.integrity import (
    IntegrityError,
    bounded_descendant,
    reject_redirecting_ancestry,
    sha256_bytes,
)
from src.modeling.evaluation import TwoModelEvaluationResult


_MANIFEST_NAME = "evidence-manifest.json"
_RESULTS_NAME = "results.json"
_SOURCE_MANIFEST_NAME = "execution-source-manifest.json"
_MATERIALIZATION_NAME = "execution-materialization-receipt.json"
_SHA256_CHARS = frozenset("0123456789abcdef")
_EVIDENCE_MEMBER_NAMES = (
    "evaluation-request.json",
    "frozen-inference-protocols.json",
    _SOURCE_MANIFEST_NAME,
    _MATERIALIZATION_NAME,
    "preauthorization-receipt.json",
    "one-shot-authorization.json",
    "one-shot-claim.json",
    "evaluation-access-receipt.json",
    "qwen-predictions.jsonl",
    "phobert-predictions.jsonl",
    _RESULTS_NAME,
    "results.md",
)


@dataclass(frozen=True, slots=True)
class ReportingAuthorityPins:
    """Trusted identities stored outside any caller-supplied evidence bundle."""

    export_manifest_sha256: str
    erratum_sha256: str
    source_tree_sha256: str


CANONICAL_REPORTING_PINS = ReportingAuthorityPins(
    export_manifest_sha256="9ac54d58c273ab0a8c2f2b4b61e472a51ca94231a94b6847637ecad6ceee49f7",
    erratum_sha256="c7be74346f0e217c382e556fbf0a730cb33be50356d4155356a5b024871a1672",
    source_tree_sha256="c3bbc8c8adaf7579fd2eb9c59a0081613be4b2cae05dfdb64472938c7e6d0434",
)


class ReportingAuthorityError(RuntimeError):
    """Raised when immutable reporting evidence fails closed."""


@dataclass(frozen=True, slots=True)
class ReportingAuthority:
    """Typed facts plus the exact bytes used to establish their identities."""

    result: TwoModelEvaluationResult
    export_manifest_sha256: str
    results_sha256: str
    source_manifest_sha256: str
    materialization_receipt_sha256: str
    erratum_sha256: str
    source_tree_sha256: str
    corrected_claim: str
    downstream_requirement: str
    retracted_claims: tuple[str, ...]
    access_impact: tuple[tuple[str, bool], ...]
    automated_access_statements: tuple[str, ...]
    refactored_source_is_metric_producer: Literal[False] = False
    export_manifest_raw: bytes = field(repr=False, default=b"")
    results_raw: bytes = field(repr=False, default=b"")
    source_manifest_raw: bytes = field(repr=False, default=b"")
    materialization_receipt_raw: bytes = field(repr=False, default=b"")
    erratum_raw: bytes = field(repr=False, default=b"")


def _json_object(raw: bytes, *, where: str) -> dict[str, Any]:
    def reject_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise ReportingAuthorityError(
                    f"{where} contains duplicate JSON key {key!r}"
                )
            result[key] = value
        return result

    try:
        value = json.loads(
            raw.decode("utf-8", errors="strict"),
            object_pairs_hook=reject_duplicates,
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ReportingAuthorityError(f"{where} must be strict UTF-8 JSON") from exc
    if not isinstance(value, dict):
        raise ReportingAuthorityError(f"{where} must be a JSON object")
    return value


def _read_json(path: Path, *, where: str) -> tuple[bytes, dict[str, Any]]:
    try:
        raw = Path(path).read_bytes()
    except OSError as exc:
        raise ReportingAuthorityError(f"cannot read {where}: {path}") from exc
    return raw, _json_object(raw, where=where)


def _require_mapping(value: object, *, where: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ReportingAuthorityError(f"{where} must be an object")
    return value


def _require_text(value: object, *, where: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ReportingAuthorityError(f"{where} must be non-empty text")
    return value


def _require_sha256(value: object, *, where: str) -> str:
    digest = _require_text(value, where=where)
    if len(digest) != 64 or any(character not in _SHA256_CHARS for character in digest):
        raise ReportingAuthorityError(f"{where} must be a lowercase SHA-256")
    return digest


def _require_literal(value: object, expected: object, *, where: str) -> None:
    if value != expected:
        raise ReportingAuthorityError(f"{where} must equal {expected!r}")


def _artifact_hashes(manifest: Mapping[str, Any]) -> dict[str, str]:
    if set(manifest) != {"artifacts", "schema_version", "status", "terminal_policy"}:
        raise ReportingAuthorityError("evidence manifest fields are not closed")
    _require_literal(
        manifest.get("schema_version"),
        "phase41-evidence-manifest-v1",
        where="evidence manifest schema_version",
    )
    _require_literal(manifest.get("status"), "completed", where="evidence manifest status")
    terminal = _require_mapping(
        manifest.get("terminal_policy"), where="evidence manifest terminal_policy"
    )
    expected_policy = {
        "rerun_permitted": False,
        "test_outcome_used_for_tuning": False,
        "unbiased_test_score_claim_after_deployment_fit": False,
    }
    if dict(terminal) != expected_policy:
        raise ReportingAuthorityError("evidence manifest terminal policy is not frozen")
    artifacts = manifest.get("artifacts")
    if not isinstance(artifacts, list):
        raise ReportingAuthorityError("evidence manifest artifacts must be a list")
    result: dict[str, str] = {}
    for index, item in enumerate(artifacts):
        entry = _require_mapping(item, where=f"evidence manifest artifact {index}")
        if set(entry) != {"name", "sha256"}:
            raise ReportingAuthorityError("evidence manifest artifact fields are not closed")
        name = _require_text(entry.get("name"), where=f"artifact {index} name")
        if name in result:
            raise ReportingAuthorityError(f"duplicate evidence artifact {name!r}")
        result[name] = _require_sha256(
            entry.get("sha256"), where=f"artifact {name!r} sha256"
        )
    if tuple(result) != _EVIDENCE_MEMBER_NAMES:
        raise ReportingAuthorityError("evidence manifest must contain the exact 12 members")
    return result


def _read_export_member(
    root: Path, name: str, expected_sha256: str
) -> tuple[bytes, dict[str, Any]]:
    try:
        path = bounded_descendant(root, Path(name), where=f"reporting member {name}")
    except IntegrityError as exc:
        raise ReportingAuthorityError(str(exc)) from exc
    raw, payload = _read_json(path, where=f"reporting member {name}")
    if sha256_bytes(raw) != expected_sha256:
        raise ReportingAuthorityError(f"reporting member {name} hash does not match manifest")
    return raw, payload


def _source_runtime_links(
    source: Mapping[str, Any]
) -> tuple[str, str, str, list[str]]:
    launcher_host = _require_mapping(
        source.get("launcher_host"), where="source manifest launcher host"
    )
    host_sha256 = _require_sha256(
        launcher_host.get("sha256"), where="source manifest launcher host sha256"
    )
    external_authority = _require_sha256(
        launcher_host.get("external_launch_receipt_sha256"),
        where="source manifest external launcher authority",
    )
    python = _require_mapping(source.get("python"), where="source manifest python")
    python_sha256 = _require_sha256(
        python.get("sha256"), where="source manifest python sha256"
    )
    runtime_import_roots = python.get("runtime_import_roots")
    if not isinstance(runtime_import_roots, list) or not all(
        isinstance(item, str) and item for item in runtime_import_roots
    ):
        raise ReportingAuthorityError("source manifest runtime import roots are invalid")
    return host_sha256, external_authority, python_sha256, runtime_import_roots


def _validate_source_chain(
    source: Mapping[str, Any], receipt: Mapping[str, Any], source_sha256: str
) -> str:
    _require_literal(
        source.get("schema_version"),
        "phase41-execution-source-manifest-v1",
        where="source manifest schema_version",
    )
    _require_literal(
        source.get("alternate_evaluators_permitted"),
        False,
        where="source manifest alternate evaluator policy",
    )
    source_tree_sha256 = _require_sha256(
        source.get("source_tree_sha256"), where="source tree sha256"
    )
    files = source.get("files")
    if not isinstance(files, list) or not files:
        raise ReportingAuthorityError("source manifest files must be a non-empty list")
    launcher = _require_mapping(source.get("launcher"), where="source manifest launcher")
    launcher_sha256 = _require_sha256(
        launcher.get("sha256"), where="source manifest launcher sha256"
    )
    (
        host_sha256,
        external_authority,
        python_sha256,
        runtime_import_roots,
    ) = _source_runtime_links(source)

    _require_literal(
        receipt.get("schema_version"),
        "phase41-execution-materialization-v1",
        where="materialization schema_version",
    )
    _require_literal(
        receipt.get("source_manifest_sha256"),
        source_sha256,
        where="materialization source manifest link",
    )
    _require_literal(
        receipt.get("source_tree_sha256"),
        source_tree_sha256,
        where="materialization source tree link",
    )
    _require_literal(
        receipt.get("launcher_sha256"),
        launcher_sha256,
        where="materialization launcher link",
    )
    _require_literal(
        receipt.get("launcher_host_sha256"),
        host_sha256,
        where="materialization launcher host link",
    )
    _require_literal(
        receipt.get("external_launcher_authority_sha256"),
        external_authority,
        where="materialization external launcher authority link",
    )
    _require_literal(
        receipt.get("python_executable_sha256"),
        python_sha256,
        where="materialization python link",
    )
    _require_literal(
        receipt.get("runtime_import_roots"),
        runtime_import_roots,
        where="materialization runtime import roots",
    )
    _require_literal(
        receipt.get("preparation_scope"),
        source.get("preparation_scope"),
        where="materialization preparation scope",
    )
    _require_literal(
        receipt.get("mode"),
        "locked-clean-runtime",
        where="materialization mode",
    )
    _require_literal(
        receipt.get("source_file_count"),
        len(files),
        where="materialization source file count",
    )
    _require_literal(
        receipt.get("source_handles_locked_at_launch"),
        True,
        where="materialization locked source handles",
    )
    return source_tree_sha256


def _validate_erratum(
    erratum: Mapping[str, Any], manifest_sha256: str
) -> tuple[str, str, tuple[str, ...], tuple[tuple[str, bool], ...], tuple[str, ...]]:
    _require_literal(
        erratum.get("schema_version"),
        "phase41-provenance-erratum-v1",
        where="erratum schema_version",
    )
    _require_literal(erratum.get("status"), "corrective_disclosure", where="erratum status")
    sealed = _require_mapping(erratum.get("sealed_export"), where="erratum sealed_export")
    _require_literal(
        sealed.get("evidence_manifest_sha256"),
        manifest_sha256,
        where="erratum evidence manifest link",
    )
    _require_literal(
        sealed.get("modified_or_resealed"), False, where="erratum reseal disposition"
    )
    _require_literal(
        sealed.get("prediction_or_metric_artifacts_modified"),
        False,
        where="erratum metric disposition",
    )
    _require_literal(
        sealed.get("erratum_location"),
        "external_non_sealed_companion",
        where="erratum companion location",
    )
    retracted = erratum.get("retracted_claims")
    if not isinstance(retracted, list) or not retracted:
        raise ReportingAuthorityError("erratum retracted claims must be a non-empty list")
    retracted_claims = tuple(
        _require_text(item, where="erratum retracted claim") for item in retracted
    )
    impact = _require_mapping(erratum.get("access_impact"), where="erratum access impact")
    if not impact or any(not isinstance(value, bool) for value in impact.values()):
        raise ReportingAuthorityError("erratum access impact values must be booleans")
    automated = erratum.get("automated_split_reads")
    if not isinstance(automated, list) or not automated:
        raise ReportingAuthorityError("erratum automated access disclosures are required")
    automated_statements = tuple(
        _require_text(
            _require_mapping(item, where="automated access disclosure").get("statement"),
            where="automated access statement",
        )
        for item in automated
    )
    return (
        _require_text(erratum.get("corrected_claim"), where="erratum corrected claim"),
        _require_text(
            erratum.get("downstream_requirement"), where="erratum downstream requirement"
        ),
        retracted_claims,
        tuple((str(key), value) for key, value in impact.items()),
        automated_statements,
    )


def _validate_result_links(
    result: TwoModelEvaluationResult, hashes: Mapping[str, str]
) -> None:
    _require_literal(
        result.prepared_sha256,
        hashes["evaluation-request.json"],
        where="results prepared request link",
    )
    _require_literal(
        result.authorization_sha256,
        hashes["one-shot-authorization.json"],
        where="results authorization link",
    )
    _require_literal(
        result.claim_sha256,
        hashes["one-shot-claim.json"],
        where="results claim link",
    )
    prediction_names = ("qwen-predictions.jsonl", "phobert-predictions.jsonl")
    for model, name in zip(result.models, prediction_names, strict=True):
        _require_literal(
            model.predictions_sha256,
            hashes[name],
            where=f"results {model.role} prediction link",
        )


def _load_reporting_authority(
    export_root: Path,
    erratum_path: Path,
    pins: ReportingAuthorityPins,
) -> ReportingAuthority:
    """Verify reporting facts against an independently trusted identity set."""

    try:
        root = reject_redirecting_ancestry(Path(export_root), where="verified export root")
        if root.parent == root or not root.is_dir():
            raise ReportingAuthorityError("verified export root must be a bounded directory")
        erratum = reject_redirecting_ancestry(Path(erratum_path), where="provenance erratum")
        if not erratum.is_file():
            raise ReportingAuthorityError("provenance erratum must be an existing file")
        manifest_path = bounded_descendant(root, Path(_MANIFEST_NAME), where="evidence manifest")
    except IntegrityError as exc:
        raise ReportingAuthorityError(str(exc)) from exc

    manifest_raw, manifest_payload = _read_json(manifest_path, where="evidence manifest")
    manifest_sha256 = sha256_bytes(manifest_raw)
    if manifest_sha256 != pins.export_manifest_sha256:
        raise ReportingAuthorityError("evidence manifest is not the canonical reporting authority")
    if root.name != manifest_sha256:
        raise ReportingAuthorityError("verified export directory identity does not match manifest")
    hashes = _artifact_hashes(manifest_payload)
    results_raw, results_payload = _read_export_member(
        root, _RESULTS_NAME, hashes[_RESULTS_NAME]
    )
    source_raw, source_payload = _read_export_member(
        root, _SOURCE_MANIFEST_NAME, hashes[_SOURCE_MANIFEST_NAME]
    )
    receipt_raw, receipt_payload = _read_export_member(
        root, _MATERIALIZATION_NAME, hashes[_MATERIALIZATION_NAME]
    )
    erratum_raw, erratum_payload = _read_json(erratum, where="provenance erratum")
    if sha256_bytes(erratum_raw) != pins.erratum_sha256:
        raise ReportingAuthorityError("provenance erratum is not the canonical disclosure")

    try:
        result = TwoModelEvaluationResult.model_validate(results_payload)
    except ValidationError as exc:
        raise ReportingAuthorityError(f"results contract failed: {exc}") from exc
    _validate_result_links(result, hashes)
    source_sha256 = sha256_bytes(source_raw)
    source_tree_sha256 = _validate_source_chain(
        source_payload, receipt_payload, source_sha256
    )
    if source_tree_sha256 != pins.source_tree_sha256:
        raise ReportingAuthorityError("source tree is not the canonical producer closure")
    (
        corrected_claim,
        downstream_requirement,
        retracted_claims,
        access_impact,
        automated_access_statements,
    ) = _validate_erratum(erratum_payload, manifest_sha256)
    return ReportingAuthority(
        result=result,
        export_manifest_sha256=manifest_sha256,
        results_sha256=sha256_bytes(results_raw),
        source_manifest_sha256=source_sha256,
        materialization_receipt_sha256=sha256_bytes(receipt_raw),
        erratum_sha256=sha256_bytes(erratum_raw),
        source_tree_sha256=source_tree_sha256,
        corrected_claim=corrected_claim,
        downstream_requirement=downstream_requirement,
        retracted_claims=retracted_claims,
        access_impact=access_impact,
        automated_access_statements=automated_access_statements,
        export_manifest_raw=manifest_raw,
        results_raw=results_raw,
        source_manifest_raw=source_raw,
        materialization_receipt_raw=receipt_raw,
        erratum_raw=erratum_raw,
    )


def load_reporting_authority(export_root: Path, erratum_path: Path) -> ReportingAuthority:
    """Return facts only from the project-pinned frozen export and erratum."""

    return _load_reporting_authority(
        export_root,
        erratum_path,
        CANONICAL_REPORTING_PINS,
    )


__all__ = [
    "ReportingAuthority",
    "ReportingAuthorityError",
    "ReportingAuthorityPins",
    "load_reporting_authority",
]
