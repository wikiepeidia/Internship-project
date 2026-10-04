"""Additive per-run authority for the final Phase 40 comparison.

The original three-run request remains immutable.  A self-contained recovery
capsule supplies the successful PhoBERT v12 request, while Qwen QLoRA remains
authorized by the original repository request.  This module resolves those
two authorities without accepting caller-selected paths and without binding
any downstream launch, model-release, or review receipts.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
from types import MappingProxyType
from typing import Any, Literal, Mapping

from pydantic import BaseModel, ConfigDict, field_validator, model_validator

from src.model_adaptation import phase40_handoff as _handoff


PHASE40_FINAL_COMPARISON_AUTHORITY_SCHEMA_VERSION = (
    "phase40-final-comparison-authority-v1"
)
FIXED_FINAL_COMPARISON_AUTHORITY_PATH = (
    "data/models/phase40/final-comparison-authority.json"
)
FIXED_ORIGINAL_REQUEST_PATH = "data/models/phase40/full-run-request.json"
FIXED_HISTORICAL_SCOPE_AMENDMENT_PATH = (
    "data/models/phase40/two-full-model-scope-amendment.json"
)
FIXED_PHOBERT_V12_CAPSULE_ROOT = (
    "data/models/phase40/request-authority-roots/phobert-v12"
)

# These identities were emitted by the independently sealed v12 recovery
# controller before this post-run comparison authority existed.  Pinning them
# prevents a structurally valid but different capsule from becoming the first
# frozen comparison truth.
EXPECTED_ORIGINAL_REQUEST_SHA256 = (
    "2512dbe6d7c5b8c16141ebdbdc848382e56b3a5737e8aeea51d7fb89447c643a"
)
EXPECTED_RECOVERY_REQUEST_SHA256 = (
    "f95f20a4094179eda62d7f255ae426d3971bc214fed19f93d30173d5fb9553e2"
)
EXPECTED_RECOVERY_SOURCE_ARCHIVE_SHA256 = (
    "0e76ee9fda535ff83e48de11a08877ba44e1ba112e52a42d54718793e67c64ac"
)
EXPECTED_RECOVERY_SOURCE_INVENTORY_SHA256 = (
    "f6181c8fa074f1c49bd2984c08e4a4163ff5095a6410268bd43e805ec82cebdf"
)
EXPECTED_SHARED_INPUT_ARCHIVE_SHA256 = (
    "12136f9a79e7c9852f6b317f284a9a018710aa66af54de4714ec66e8cf92bf84"
)
EXPECTED_SHARED_INPUT_MANIFEST_SHA256 = (
    "a53b2930e30c1bb28894262559e38ebde419cace547da6fc7f17ac75b1d72614"
)

ORIGINAL_REQUEST_AUTHORITY_ID = "qwen-v1-origin"
RECOVERY_REQUEST_AUTHORITY_ID = "phobert-v12-recovery"
QWEN_QLORA_RUN_ID = "phase40-qwen-qlora-full-seed42-v1"
QWEN_LORA_RUN_ID = "phase40-qwen-lora-full-seed42-v1"
ORIGINAL_PHOBERT_RUN_ID = "phase40-phobert-full-seed42-v1"
RECOVERY_PHOBERT_RUN_ID = "phase40-phobert-full-seed42-v12"
QWEN_QLORA_RETURNED_ROOT = "data/models/phase40/full/qwen-qlora"
PHOBERT_RETURNED_ROOT = "data/models/phase40/full/phobert"
_QWEN_LORA_RETURNED_ROOT = "data/models/phase40/full/qwen-lora"
_RECOVERY_POLICY = "additive_per_run_request_authority_no_evidence_rewrite_v1"
_SOURCE_TREE_DOMAIN = b"phase40-comparison-finalizer-source-v1\0"
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_SOURCE_CONTROL_NAMES = ("source_archive_sha256", "source_inventory_sha256")


def _canonical_json_bytes(value: object) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        + "\n"
    ).encode("utf-8")


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _require_sha256(value: str, *, where: str) -> str:
    if not isinstance(value, str) or not _SHA256_RE.fullmatch(value):
        raise ValueError(f"{where} must be 64 lowercase hexadecimal characters")
    return value


def _reject_duplicate_keys(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _strict_json_object(payload: bytes, *, where: str) -> dict[str, object]:
    try:
        value = json.loads(
            payload.decode("utf-8", errors="strict"),
            object_pairs_hook=_reject_duplicate_keys,
        )
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        raise ValueError(f"{where} is not strict duplicate-free JSON") from exc
    if not isinstance(value, dict):
        raise ValueError(f"{where} must be one JSON object")
    return value


class RequestAuthorityReference(BaseModel):
    """One fixed root policy and the exact canonical request bytes below it."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    authority_id: str
    root_policy: Literal["repository_root", "fixed_phobert_v12_capsule"]
    request_sha256: str

    @field_validator("request_sha256")
    @classmethod
    def validate_request_sha256(cls, value: str) -> str:
        return _require_sha256(value, where="request authority SHA-256")


class SelectedRunReference(BaseModel):
    """A final run selected from exactly one request authority."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    run_id: str
    request_authority_id: str
    requested_run_id: str
    returned_root: str


class SupersededScopeAmendmentReference(BaseModel):
    """Hash reference to the historical, source-stale two-model amendment."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    relative_path: Literal[
        "data/models/phase40/two-full-model-scope-amendment.json"
    ] = FIXED_HISTORICAL_SCOPE_AMENDMENT_PATH
    sha256: str
    schema_version: Literal["phase40-two-full-model-scope-amendment-v1"] = (
        "phase40-two-full-model-scope-amendment-v1"
    )

    @field_validator("sha256")
    @classmethod
    def validate_sha256(cls, value: str) -> str:
        return _require_sha256(value, where="historical scope-amendment SHA-256")


class HistoricalComparisonFinalizerAuthority(BaseModel):
    """Self-consistent historical source pin, deliberately not checked live."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["phase40-comparison-finalizer-authority-v1"] = (
        "phase40-comparison-finalizer-authority-v1"
    )
    runtime_origin: Literal[
        "local_hash_pinned_source_not_training_runtime_v3"
    ] = "local_hash_pinned_source_not_training_runtime_v3"
    files: tuple[_handoff.SourceInventoryEntry, ...]
    source_tree_sha256: str

    @field_validator("source_tree_sha256")
    @classmethod
    def validate_source_tree_sha256(cls, value: str) -> str:
        return _require_sha256(value, where="historical finalizer source-tree SHA-256")

    @model_validator(mode="after")
    def validate_internal_tree(self) -> "HistoricalComparisonFinalizerAuthority":
        paths = tuple(entry.path for entry in self.files)
        if not paths or paths != tuple(sorted(paths)) or len(paths) != len(set(paths)):
            raise ValueError(
                "historical comparison-finalizer inventory must be non-empty, unique, and sorted"
            )
        expected = _sha256(
            _SOURCE_TREE_DOMAIN
            + _canonical_json_bytes(
                [entry.model_dump(mode="json") for entry in self.files]
            )
        )
        if self.source_tree_sha256 != expected:
            raise ValueError(
                "historical comparison-finalizer source-tree hash differs from its inventory"
            )
        return self


class HistoricalScopeAmendment(BaseModel):
    """Strict historical policy schema with a non-live old source inventory."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["phase40-two-full-model-scope-amendment-v1"]
    original_run_request_path: Literal[
        "data/models/phase40/full-run-request.json"
    ]
    original_run_request_sha256: str
    active_full_run_ids: tuple[
        Literal["phase40-qwen-qlora-full-seed42-v1"],
        Literal["phase40-phobert-full-seed42-v1"],
    ]
    active_returned_roots: tuple[
        Literal["data/models/phase40/full/qwen-qlora"],
        Literal["data/models/phase40/full/phobert"],
    ]
    waived_full_run_id: Literal["phase40-qwen-lora-full-seed42-v1"]
    waived_returned_root: Literal["data/models/phase40/full/qwen-lora"]
    full_lora_disposition: Literal["cancelled_before_start"]
    waiver_action: Literal["withdrawn"]
    waiver_basis: Literal[
        "bounded_local_probe_established_resource_pressure_and_deadline_mismatch"
    ]
    lora_probe_authority: _handoff.LoraProbeAuthority
    comparison_finalizer_authority: HistoricalComparisonFinalizerAuthority
    quality_model_run_ids: tuple[
        Literal["phase40-qwen-qlora-full-seed42-v1"],
        Literal["phase40-phobert-full-seed42-v1"],
    ]
    review_model_run_ids: tuple[
        Literal["phase40-qwen-qlora-full-seed42-v1"],
        Literal["phase40-phobert-full-seed42-v1"],
    ]
    execution_policy: Literal["local_primary"]
    colab_contingency_policy: Literal[
        "validation_only_before_held_out_open_if_local_quality_unacceptable"
    ]
    no_held_out_boundary: Literal[True]

    @field_validator("original_run_request_sha256")
    @classmethod
    def validate_request_sha256(cls, value: str) -> str:
        return _require_sha256(value, where="historical original-request SHA-256")


class Phase40FinalComparisonAuthority(BaseModel):
    """Canonical selection of two runs across two immutable request roots."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["phase40-final-comparison-authority-v1"] = (
        PHASE40_FINAL_COMPARISON_AUTHORITY_SCHEMA_VERSION
    )
    superseded_scope_amendment: SupersededScopeAmendmentReference
    request_authorities: tuple[RequestAuthorityReference, RequestAuthorityReference]
    selected_runs: tuple[SelectedRunReference, SelectedRunReference]
    quality_model_run_ids: tuple[
        Literal["phase40-qwen-qlora-full-seed42-v1"],
        Literal["phase40-phobert-full-seed42-v12"],
    ]
    review_model_run_ids: tuple[
        Literal["phase40-qwen-qlora-full-seed42-v1"],
        Literal["phase40-phobert-full-seed42-v12"],
    ]
    shared_input_authority: _handoff.InputBundleReference
    waived_full_run_id: Literal["phase40-qwen-lora-full-seed42-v1"]
    waiver_action: Literal["withdrawn"]
    lora_probe_authority: _handoff.LoraProbeAuthority
    comparison_finalizer_authority: _handoff.ComparisonFinalizerAuthority
    recovery_policy: Literal[
        "additive_per_run_request_authority_no_evidence_rewrite_v1"
    ] = _RECOVERY_POLICY
    execution_policy: Literal["local_primary"] = "local_primary"
    no_held_out_boundary: Literal[True] = True

    @model_validator(mode="after")
    def validate_fixed_selection(self) -> "Phase40FinalComparisonAuthority":
        request_pairs = tuple(
            (entry.authority_id, entry.root_policy)
            for entry in self.request_authorities
        )
        if request_pairs != (
            (ORIGINAL_REQUEST_AUTHORITY_ID, "repository_root"),
            (RECOVERY_REQUEST_AUTHORITY_ID, "fixed_phobert_v12_capsule"),
        ):
            raise ValueError("request authorities must equal the two fixed roots in order")
        selected = tuple(
            (
                entry.run_id,
                entry.request_authority_id,
                entry.requested_run_id,
                entry.returned_root,
            )
            for entry in self.selected_runs
        )
        if selected != (
            (
                QWEN_QLORA_RUN_ID,
                ORIGINAL_REQUEST_AUTHORITY_ID,
                QWEN_QLORA_RUN_ID,
                QWEN_QLORA_RETURNED_ROOT,
            ),
            (
                RECOVERY_PHOBERT_RUN_ID,
                RECOVERY_REQUEST_AUTHORITY_ID,
                RECOVERY_PHOBERT_RUN_ID,
                PHOBERT_RETURNED_ROOT,
            ),
        ):
            raise ValueError("selected runs must equal Qwen QLoRA v1 and PhoBERT v12")
        expected_ids = (QWEN_QLORA_RUN_ID, RECOVERY_PHOBERT_RUN_ID)
        if self.quality_model_run_ids != expected_ids or self.review_model_run_ids != expected_ids:
            raise ValueError("quality and review model IDs must equal the selected runs")
        return self


@dataclass(frozen=True, slots=True)
class ResolvedRunAuthority:
    """One selected run and all authority objects derived from its origin request."""

    run_id: str
    origin: RequestAuthorityReference
    origin_request: _handoff.RunRequest
    requested_run: _handoff.FullRunRequestIdentity
    control_template: _handoff.RequestedControlTemplate
    transfer_authority: _handoff.TransferAuthorityEvidence


@dataclass(frozen=True, slots=True)
class VerifiedPhase40FinalComparisonAuthority:
    """Verified authority plus immutable per-run resolutions."""

    authority: Phase40FinalComparisonAuthority
    authority_sha256: str
    historical_scope_amendment: HistoricalScopeAmendment
    original_request: _handoff.RunRequest
    recovery_request: _handoff.RunRequest
    runs: tuple[ResolvedRunAuthority, ResolvedRunAuthority]

    @property
    def by_run_id(self) -> Mapping[str, ResolvedRunAuthority]:
        return MappingProxyType({run.run_id: run for run in self.runs})


def _fixed_regular_file(root: Path, relative: str, *, where: str) -> Path:
    fixed = PurePosixPath(relative)
    if fixed.is_absolute() or not fixed.parts or ".." in fixed.parts or "\\" in relative:
        raise RuntimeError(f"internal {where} path is not a safe fixed relative path")
    trusted_root = _handoff._trusted_repo_root(root)
    path = Path(
        os.path.abspath(os.path.normpath(os.fspath(trusted_root / fixed)))
    )
    try:
        path.relative_to(trusted_root)
    except ValueError as exc:
        raise RuntimeError(f"internal {where} path escaped its fixed root") from exc
    _handoff._reject_redirecting_path_components((path,))
    if not path.is_file() or path.is_symlink():
        raise ValueError(f"{where} is not the fixed regular file")
    return path


def _load_strict_request(root: Path, *, where: str) -> tuple[bytes, _handoff.RunRequest]:
    request = _handoff.load_frozen_phase40_run_request(repo_root=root)
    path = _fixed_regular_file(root, FIXED_ORIGINAL_REQUEST_PATH, where=where)
    payload = path.read_bytes()
    parsed = _handoff.RunRequest.model_validate(_strict_json_object(payload, where=where))
    if payload != _canonical_json_bytes(parsed.model_dump(mode="json")):
        raise ValueError(f"{where} bytes are not canonical JSON")
    if parsed != request:
        raise RuntimeError(f"{where} changed during strict verification")
    return payload, request


def _load_historical_amendment(
    root: Path,
) -> tuple[bytes, HistoricalScopeAmendment]:
    path = _fixed_regular_file(
        root,
        FIXED_HISTORICAL_SCOPE_AMENDMENT_PATH,
        where="historical Phase 40 scope amendment",
    )
    payload = path.read_bytes()
    amendment = HistoricalScopeAmendment.model_validate(
        _strict_json_object(payload, where="historical Phase 40 scope amendment")
    )
    if payload != _canonical_json_bytes(amendment.model_dump(mode="json")):
        raise ValueError("historical Phase 40 scope-amendment bytes are not canonical JSON")
    return payload, amendment


def _by_run_id(request: _handoff.RunRequest) -> dict[str, _handoff.FullRunRequestIdentity]:
    return {run.run_id: run for run in request.runs}


def _require_exact_request_run_ids(
    original: _handoff.RunRequest,
    recovery: _handoff.RunRequest,
) -> None:
    if tuple(run.run_id for run in original.runs) != (
        QWEN_LORA_RUN_ID,
        QWEN_QLORA_RUN_ID,
        ORIGINAL_PHOBERT_RUN_ID,
    ):
        raise ValueError("original request run IDs/order drifted")
    if tuple(run.run_id for run in recovery.runs) != (
        QWEN_LORA_RUN_ID,
        QWEN_QLORA_RUN_ID,
        RECOVERY_PHOBERT_RUN_ID,
    ):
        raise ValueError("recovery request run IDs/order drifted")


def _require_source_controls(
    template: _handoff.RequestedControlTemplate,
    request: _handoff.RunRequest,
    *,
    where: str,
) -> None:
    controls = template.controls_without_accelerator.get("additional_controls")
    if not isinstance(controls, list):
        raise ValueError(f"{where} additional_controls must be a list")
    values: dict[str, object] = {}
    for entry in controls:
        if not isinstance(entry, dict):
            raise ValueError(f"{where} additional control must be an object")
        name = entry.get("name")
        if name in _SOURCE_CONTROL_NAMES:
            if name in values:
                raise ValueError(f"{where} repeats {name}")
            values[str(name)] = entry.get("value")
    expected = {
        "source_archive_sha256": request.source_bundle.archive_sha256,
        "source_inventory_sha256": request.source_bundle.inventory_sha256,
    }
    if values != expected:
        raise ValueError(f"{where} source controls differ from its request source authority")


def _expected_recovery_phobert_template(
    original: _handoff.RequestedControlTemplate,
    recovery_request: _handoff.RunRequest,
) -> _handoff.RequestedControlTemplate:
    payload = original.model_dump(mode="json")
    controls = payload["controls_without_accelerator"]["additional_controls"]
    replacements = {
        "source_archive_sha256": recovery_request.source_bundle.archive_sha256,
        "source_inventory_sha256": recovery_request.source_bundle.inventory_sha256,
    }
    replaced: set[str] = set()
    for entry in controls:
        name = entry.get("name")
        if name in replacements:
            if name in replaced:
                raise ValueError(f"original PhoBERT template repeats {name}")
            entry["value"] = replacements[name]
            replaced.add(name)
    if replaced != set(_SOURCE_CONTROL_NAMES):
        raise ValueError("original PhoBERT template lacks the exact source controls")
    return _handoff.RequestedControlTemplate.model_validate(payload)


def _verify_recovery_delta(
    original: _handoff.RunRequest,
    recovery: _handoff.RunRequest,
) -> None:
    _require_exact_request_run_ids(original, recovery)
    if original.source_bundle == recovery.source_bundle:
        raise ValueError("recovery request must bind its independently frozen source bundle")
    if (
        original.input_bundle != recovery.input_bundle
        or original.package_candidates != recovery.package_candidates
        or original.expected_bundle_files != recovery.expected_bundle_files
        or original.no_held_out_boundary != recovery.no_held_out_boundary
        or original.git_commit != recovery.git_commit
    ):
        raise ValueError(
            "recovery request differs outside source, PhoBERT run ID, and PhoBERT source controls"
        )

    original_runs = _by_run_id(original)
    recovery_runs = _by_run_id(recovery)
    for run_id in (QWEN_LORA_RUN_ID, QWEN_QLORA_RUN_ID):
        if original_runs[run_id] != recovery_runs[run_id]:
            raise ValueError(f"recovery request changed Qwen run identity: {run_id}")
        if (
            _canonical_json_bytes(
                original.control_template_by_run[run_id].model_dump(mode="json")
            )
            != _canonical_json_bytes(
                recovery.control_template_by_run[run_id].model_dump(mode="json")
            )
            or original.control_template_digest_by_run[run_id]
            != recovery.control_template_digest_by_run[run_id]
        ):
            raise ValueError(f"recovery request changed Qwen controls: {run_id}")

    original_phobert = original_runs[ORIGINAL_PHOBERT_RUN_ID]
    recovery_phobert = recovery_runs[RECOVERY_PHOBERT_RUN_ID]
    expected_run = original_phobert.model_copy(update={"run_id": RECOVERY_PHOBERT_RUN_ID})
    if recovery_phobert != expected_run:
        raise ValueError("PhoBERT recovery run differs beyond its v12 run ID")

    original_template = original.control_template_by_run[ORIGINAL_PHOBERT_RUN_ID]
    recovery_template = recovery.control_template_by_run[RECOVERY_PHOBERT_RUN_ID]
    _require_source_controls(original_template, original, where="original PhoBERT template")
    _require_source_controls(recovery_template, recovery, where="recovery PhoBERT template")
    if recovery_template != _expected_recovery_phobert_template(original_template, recovery):
        raise ValueError("PhoBERT recovery controls differ beyond the two source hashes")
    if (
        original.control_template_digest_by_run[ORIGINAL_PHOBERT_RUN_ID]
        != original_template.sha256
        or recovery.control_template_digest_by_run[RECOVERY_PHOBERT_RUN_ID]
        != recovery_template.sha256
    ):
        raise ValueError("PhoBERT template digest is not derived from its exact controls")

    if set(original.control_template_by_run) != {
        QWEN_LORA_RUN_ID,
        QWEN_QLORA_RUN_ID,
        ORIGINAL_PHOBERT_RUN_ID,
    } or set(recovery.control_template_by_run) != {
        QWEN_LORA_RUN_ID,
        QWEN_QLORA_RUN_ID,
        RECOVERY_PHOBERT_RUN_ID,
    }:
        raise ValueError("request control-template mapping contains an unexpected run")


def _verify_historical_policy(
    amendment: HistoricalScopeAmendment,
    *,
    original_request_sha256: str,
    repo_root: Path,
) -> _handoff.LoraProbeComparisonRecord:
    if amendment.original_run_request_sha256 != original_request_sha256:
        raise ValueError("historical scope amendment binds a different original request")
    # The old finalizer inventory is intentionally not opened.  Its immutable
    # bytes are superseded by the separate live authority in the new document.
    return _handoff.verify_lora_probe_authority(
        amendment.lora_probe_authority,
        repo_root=repo_root,
    )


def _build_live_finalizer_authority(
    repo_root: Path,
) -> _handoff.ComparisonFinalizerAuthority:
    """Prove import closure and hash the code-fixed live inventory.

    The frozen inventory also includes the external launcher itself, so the
    pre-Python PowerShell gate cannot authorize bytes that were absent from the
    reviewed authority-establishment event.
    """

    _handoff._assert_comparison_finalizer_import_closed(repo_root)

    paths = tuple(
        repo_root / PurePosixPath(relative)
        for relative in _handoff.PHASE40_COMPARISON_FINALIZER_SOURCE_ALLOWLIST
    )
    _handoff._reject_redirecting_path_components(paths)
    entries: list[_handoff.SourceInventoryEntry] = []
    for relative, path in zip(
        _handoff.PHASE40_COMPARISON_FINALIZER_SOURCE_ALLOWLIST,
        paths,
        strict=True,
    ):
        if not path.is_file() or path.is_symlink():
            raise ValueError(f"live comparison-finalizer source is missing or unsafe: {relative}")
        payload = path.read_bytes()
        entries.append(
            _handoff.SourceInventoryEntry(
                path=relative,
                bytes=len(payload),
                sha256=_sha256(payload),
            )
        )
    files = tuple(entries)
    return _handoff.ComparisonFinalizerAuthority(
        files=files,
        source_tree_sha256=_sha256(
            _SOURCE_TREE_DOMAIN
            + _canonical_json_bytes(
                [entry.model_dump(mode="json") for entry in files]
            )
        ),
    )


def _verify_live_finalizer_authority(
    authority: _handoff.ComparisonFinalizerAuthority,
    *,
    repo_root: Path,
) -> None:
    if _build_live_finalizer_authority(repo_root) != authority:
        raise ValueError("local comparison finalizer source differs from the final authority")


def _request_roots(repo_root: Path) -> tuple[Path, Path]:
    original_root = _handoff._trusted_repo_root(repo_root)
    capsule = Path(
        os.path.abspath(
            os.path.normpath(
                os.fspath(original_root / PurePosixPath(FIXED_PHOBERT_V12_CAPSULE_ROOT))
            )
        )
    )
    recovery_root = _handoff._trusted_repo_root(capsule)
    return original_root, recovery_root


def _authority_components(
    *,
    repo_root: Path,
) -> tuple[
    Path,
    bytes,
    _handoff.RunRequest,
    bytes,
    _handoff.RunRequest,
    bytes,
    HistoricalScopeAmendment,
]:
    root, recovery_root = _request_roots(repo_root)
    original_bytes, original = _load_strict_request(
        root, where="original Phase 40 run request"
    )
    recovery_bytes, recovery = _load_strict_request(
        recovery_root, where="PhoBERT v12 recovery run request"
    )
    if _sha256(original_bytes) != EXPECTED_ORIGINAL_REQUEST_SHA256:
        raise ValueError("original Phase 40 request differs from its sealed identity")
    if _sha256(recovery_bytes) != EXPECTED_RECOVERY_REQUEST_SHA256:
        raise ValueError("PhoBERT v12 request differs from its sealed recovery identity")
    if (
        recovery.source_bundle.archive_sha256
        != EXPECTED_RECOVERY_SOURCE_ARCHIVE_SHA256
        or recovery.source_bundle.inventory_sha256
        != EXPECTED_RECOVERY_SOURCE_INVENTORY_SHA256
    ):
        raise ValueError("PhoBERT v12 source differs from its sealed recovery identity")
    for request in (original, recovery):
        if (
            request.input_bundle.archive_sha256
            != EXPECTED_SHARED_INPUT_ARCHIVE_SHA256
            or request.input_bundle.manifest_sha256
            != EXPECTED_SHARED_INPUT_MANIFEST_SHA256
        ):
            raise ValueError("Phase 40 request differs from the sealed shared input identity")
    _verify_recovery_delta(original, recovery)
    amendment_bytes, amendment = _load_historical_amendment(root)
    _verify_historical_policy(
        amendment,
        original_request_sha256=_sha256(original_bytes),
        repo_root=root,
    )
    return (
        root,
        original_bytes,
        original,
        recovery_bytes,
        recovery,
        amendment_bytes,
        amendment,
    )


def build_phase40_final_comparison_authority(
    *, repo_root: Path
) -> Phase40FinalComparisonAuthority:
    """Derive the final authority from both fixed roots and live source code."""

    (
        root,
        original_bytes,
        original,
        recovery_bytes,
        recovery,
        amendment_bytes,
        amendment,
    ) = _authority_components(repo_root=repo_root)
    authority = Phase40FinalComparisonAuthority(
        superseded_scope_amendment=SupersededScopeAmendmentReference(
            sha256=_sha256(amendment_bytes)
        ),
        request_authorities=(
            RequestAuthorityReference(
                authority_id=ORIGINAL_REQUEST_AUTHORITY_ID,
                root_policy="repository_root",
                request_sha256=_sha256(original_bytes),
            ),
            RequestAuthorityReference(
                authority_id=RECOVERY_REQUEST_AUTHORITY_ID,
                root_policy="fixed_phobert_v12_capsule",
                request_sha256=_sha256(recovery_bytes),
            ),
        ),
        selected_runs=(
            SelectedRunReference(
                run_id=QWEN_QLORA_RUN_ID,
                request_authority_id=ORIGINAL_REQUEST_AUTHORITY_ID,
                requested_run_id=QWEN_QLORA_RUN_ID,
                returned_root=QWEN_QLORA_RETURNED_ROOT,
            ),
            SelectedRunReference(
                run_id=RECOVERY_PHOBERT_RUN_ID,
                request_authority_id=RECOVERY_REQUEST_AUTHORITY_ID,
                requested_run_id=RECOVERY_PHOBERT_RUN_ID,
                returned_root=PHOBERT_RETURNED_ROOT,
            ),
        ),
        quality_model_run_ids=(QWEN_QLORA_RUN_ID, RECOVERY_PHOBERT_RUN_ID),
        review_model_run_ids=(QWEN_QLORA_RUN_ID, RECOVERY_PHOBERT_RUN_ID),
        shared_input_authority=original.input_bundle,
        waived_full_run_id=amendment.waived_full_run_id,
        waiver_action=amendment.waiver_action,
        lora_probe_authority=amendment.lora_probe_authority,
        comparison_finalizer_authority=_build_live_finalizer_authority(root),
    )
    verify_phase40_final_comparison_authority(authority, repo_root=root)
    return authority


def verify_phase40_final_comparison_authority(
    authority: Phase40FinalComparisonAuthority,
    *,
    repo_root: Path,
) -> VerifiedPhase40FinalComparisonAuthority:
    """Verify all fixed roots and derive authority independently for each run."""

    typed = (
        authority
        if isinstance(authority, Phase40FinalComparisonAuthority)
        else Phase40FinalComparisonAuthority.model_validate(authority)
    )
    (
        root,
        original_bytes,
        original,
        recovery_bytes,
        recovery,
        amendment_bytes,
        amendment,
    ) = _authority_components(repo_root=repo_root)

    request_hashes = tuple(entry.request_sha256 for entry in typed.request_authorities)
    if request_hashes != (_sha256(original_bytes), _sha256(recovery_bytes)):
        raise ValueError("final authority request hashes differ from the two fixed roots")
    if typed.superseded_scope_amendment.sha256 != _sha256(amendment_bytes):
        raise ValueError("final authority historical scope-amendment hash mismatch")
    if typed.shared_input_authority != original.input_bundle:
        raise ValueError("final authority shared input differs from the two requests")
    if original.input_bundle != recovery.input_bundle:
        raise ValueError("original and recovery requests do not share the exact input authority")
    if (
        typed.waived_full_run_id != amendment.waived_full_run_id
        or typed.waiver_action != amendment.waiver_action
        or typed.lora_probe_authority != amendment.lora_probe_authority
    ):
        raise ValueError("final authority changed the historical LoRA waiver or probe")
    _verify_live_finalizer_authority(
        typed.comparison_finalizer_authority,
        repo_root=root,
    )

    requests = {
        ORIGINAL_REQUEST_AUTHORITY_ID: original,
        RECOVERY_REQUEST_AUTHORITY_ID: recovery,
    }
    origins = {entry.authority_id: entry for entry in typed.request_authorities}
    resolved: list[ResolvedRunAuthority] = []
    for selection in typed.selected_runs:
        request = requests[selection.request_authority_id]
        requested_by_id = _by_run_id(request)
        requested = requested_by_id.get(selection.requested_run_id)
        if requested is None or requested.run_id != selection.run_id:
            raise ValueError(f"selected run is absent from its origin request: {selection.run_id}")
        if requested.returned_root != selection.returned_root:
            raise ValueError(f"selected returned root differs from its request: {selection.run_id}")
        template = request.control_template_by_run[selection.requested_run_id]
        if request.control_template_digest_by_run[selection.requested_run_id] != template.sha256:
            raise ValueError(f"selected template digest mismatch: {selection.run_id}")
        resolved.append(
            ResolvedRunAuthority(
                run_id=selection.run_id,
                origin=origins[selection.request_authority_id],
                origin_request=request,
                requested_run=requested,
                control_template=template,
                transfer_authority=_handoff.transfer_authority_from_request(request),
            )
        )

    return VerifiedPhase40FinalComparisonAuthority(
        authority=typed,
        authority_sha256=_sha256(_canonical_json_bytes(typed.model_dump(mode="json"))),
        historical_scope_amendment=amendment,
        original_request=original,
        recovery_request=recovery,
        runs=(resolved[0], resolved[1]),
    )


def _authority_path(root: Path, *, must_exist: bool) -> Path:
    path = Path(
        os.path.abspath(
            os.path.normpath(
                os.fspath(root / PurePosixPath(FIXED_FINAL_COMPARISON_AUTHORITY_PATH))
            )
        )
    )
    if must_exist:
        return _fixed_regular_file(
            root,
            FIXED_FINAL_COMPARISON_AUTHORITY_PATH,
            where="final Phase 40 comparison authority",
        )
    if path.parent.exists():
        _handoff._reject_redirecting_path_components((path.parent,))
    if path.exists() and (not path.is_file() or path.is_symlink()):
        raise ValueError("final Phase 40 comparison authority path is unsafe")
    return path


def freeze_phase40_final_comparison_authority(*, repo_root: Path) -> Path:
    """Write the derived authority once; only byte-identical replay is allowed."""

    root = _handoff._trusted_repo_root(repo_root)
    authority = build_phase40_final_comparison_authority(repo_root=root)
    payload = _canonical_json_bytes(authority.model_dump(mode="json"))
    destination = _authority_path(root, must_exist=False)
    if destination.exists():
        if destination.read_bytes() != payload:
            raise RuntimeError("refusing to replace a different final comparison authority")
        load_frozen_phase40_final_comparison_authority(repo_root=root)
        return destination
    destination.parent.mkdir(parents=True, exist_ok=True)
    _handoff._reject_redirecting_path_components((destination.parent,))
    try:
        with destination.open("xb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
    except FileExistsError:
        if not destination.is_file() or destination.is_symlink() or destination.read_bytes() != payload:
            raise RuntimeError("final comparison authority changed during create-only write")
    load_frozen_phase40_final_comparison_authority(repo_root=root)
    return destination


def load_frozen_phase40_final_comparison_authority(
    *, repo_root: Path
) -> VerifiedPhase40FinalComparisonAuthority:
    """Load only the code-fixed authority path and reverify every upstream root."""

    root = _handoff._trusted_repo_root(repo_root)
    path = _authority_path(root, must_exist=True)
    payload = path.read_bytes()
    authority = Phase40FinalComparisonAuthority.model_validate(
        _strict_json_object(payload, where="final Phase 40 comparison authority")
    )
    if payload != _canonical_json_bytes(authority.model_dump(mode="json")):
        raise ValueError("final Phase 40 comparison authority bytes are not canonical JSON")
    verified = verify_phase40_final_comparison_authority(authority, repo_root=root)
    if verified.authority_sha256 != _sha256(payload):
        raise RuntimeError("final comparison authority changed during verification")
    return verified


__all__ = [
    "EXPECTED_ORIGINAL_REQUEST_SHA256",
    "EXPECTED_RECOVERY_REQUEST_SHA256",
    "EXPECTED_RECOVERY_SOURCE_ARCHIVE_SHA256",
    "EXPECTED_RECOVERY_SOURCE_INVENTORY_SHA256",
    "EXPECTED_SHARED_INPUT_ARCHIVE_SHA256",
    "EXPECTED_SHARED_INPUT_MANIFEST_SHA256",
    "FIXED_FINAL_COMPARISON_AUTHORITY_PATH",
    "FIXED_HISTORICAL_SCOPE_AMENDMENT_PATH",
    "FIXED_ORIGINAL_REQUEST_PATH",
    "FIXED_PHOBERT_V12_CAPSULE_ROOT",
    "HistoricalScopeAmendment",
    "ORIGINAL_REQUEST_AUTHORITY_ID",
    "PHASE40_FINAL_COMPARISON_AUTHORITY_SCHEMA_VERSION",
    "Phase40FinalComparisonAuthority",
    "QWEN_QLORA_RUN_ID",
    "RECOVERY_PHOBERT_RUN_ID",
    "RECOVERY_REQUEST_AUTHORITY_ID",
    "RequestAuthorityReference",
    "ResolvedRunAuthority",
    "SelectedRunReference",
    "SupersededScopeAmendmentReference",
    "VerifiedPhase40FinalComparisonAuthority",
    "build_phase40_final_comparison_authority",
    "freeze_phase40_final_comparison_authority",
    "load_frozen_phase40_final_comparison_authority",
    "verify_phase40_final_comparison_authority",
]
