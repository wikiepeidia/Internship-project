"""Fixed-path verification closure for Phase 40 production authorities.

The individual Phase 40 producers deliberately own their detailed schemas and
verification logic.  This module composes those verifiers without accepting a
caller-selected receipt, manifest, bundle, or runtime-authority path.  Callers
may supply only the three disjoint trust roots needed to locate repository,
Qwen-export, and PhoBERT-transfer artifacts.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
from typing import Any, Literal, Mapping

from src.model_adaptation.phase40_comparison_launch import (
    FIXED_RECEIPT_RELATIVE_PATH as COMPARISON_LAUNCH_RECEIPT_RELATIVE_PATH,
    verify_phase40_comparison_launch_receipt,
)
from src.model_adaptation.phase40_gguf import (
    GGUFVerificationContext,
    QWEN_GGUF_VERIFICATION_RECEIPT_RELATIVE_PATH,
    load_phase40_qwen_gguf_verification_receipt,
    verify_phase40_qwen_gguf_verification_receipt,
)
from src.model_adaptation.phase40_phobert_release import (
    load_phobert_release_receipt,
    verify_phobert_release_bundle,
)
from src.model_adaptation.phase40_release_authorities import (
    RUNTIME_AUTHORITY_FILENAME,
    load_runtime_dependency_authority,
)
from src.model_adaptation.phase40_runtime_materialize import (
    MATERIALIZATION_RECEIPT_RELATIVE_PATH,
    load_runtime_materialization_receipt,
)


QWEN_GGUF_EXPORT_MANIFEST_RELATIVE_PATH = PurePosixPath(
    "qwen-qlora-q8_0.gguf.manifest.json"
)
RUNTIME_DEPENDENCY_AUTHORITY_RELATIVE_PATH = PurePosixPath(
    "data/models/phase40"
) / RUNTIME_AUTHORITY_FILENAME
RUNTIME_MATERIALIZATION_RECEIPT_RELATIVE_PATH = (
    MATERIALIZATION_RECEIPT_RELATIVE_PATH
)

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_QWEN_CHECKPOINT_RE = re.compile(r"^adapter-state-sha256:[0-9a-f]{64}$")
_PHOBERT_CHECKPOINT_RE = re.compile(r"^model-state-sha256:[0-9a-f]{64}$")
_WINDOWS_REPARSE_POINT = 0x00000400
PORTABLE_RECEIPTS_ONLY = "portable_receipts_only"
EXTERNAL_MODELS_PORTABLE_RUNTIME = "external_models_verified_portable_runtime_only"


class Phase40ProductionAuthorityError(RuntimeError):
    """Raised when the fixed Phase 40 production closure cannot be verified."""


@dataclass(frozen=True, slots=True)
class VerifiedPhase40ProductionAuthorities:
    """Typed closure with an explicit verification-strength declaration."""

    verification_mode: Literal[
        "portable_receipts_only",
        "external_models_verified_portable_runtime_only",
    ]
    comparison_launch_receipt_sha256: str
    qwen_gguf_verification_receipt_sha256: str
    phobert_release_receipt_authority_sha256: str
    phobert_segmenter_authority_sha256: str
    runtime_dependency_authority_sha256: str
    runtime_materialization_receipt_sha256: str
    qwen_selected_checkpoint_identity: str
    phobert_selected_checkpoint_identity: str
    phobert_selected_artifact_sha256: str

    def __post_init__(self) -> None:
        if self.verification_mode not in {
            PORTABLE_RECEIPTS_ONLY,
            EXTERNAL_MODELS_PORTABLE_RUNTIME,
        }:
            raise Phase40ProductionAuthorityError(
                "production authority verification mode is invalid"
            )
        for name in (
            "comparison_launch_receipt_sha256",
            "qwen_gguf_verification_receipt_sha256",
            "phobert_release_receipt_authority_sha256",
            "phobert_segmenter_authority_sha256",
            "runtime_dependency_authority_sha256",
            "runtime_materialization_receipt_sha256",
            "phobert_selected_artifact_sha256",
        ):
            _require_sha256(getattr(self, name), where=name)
        if not _QWEN_CHECKPOINT_RE.fullmatch(
            self.qwen_selected_checkpoint_identity
        ):
            raise Phase40ProductionAuthorityError(
                "selected Qwen checkpoint identity is invalid"
            )
        if not _PHOBERT_CHECKPOINT_RE.fullmatch(
            self.phobert_selected_checkpoint_identity
        ):
            raise Phase40ProductionAuthorityError(
                "selected PhoBERT checkpoint identity is invalid"
            )

    def as_dict(self) -> dict[str, str]:
        return {
            "verification_mode": self.verification_mode,
            "comparison_launch_receipt_sha256": (
                self.comparison_launch_receipt_sha256
            ),
            "qwen_gguf_verification_receipt_sha256": (
                self.qwen_gguf_verification_receipt_sha256
            ),
            "phobert_release_receipt_authority_sha256": (
                self.phobert_release_receipt_authority_sha256
            ),
            "phobert_segmenter_authority_sha256": (
                self.phobert_segmenter_authority_sha256
            ),
            "runtime_dependency_authority_sha256": (
                self.runtime_dependency_authority_sha256
            ),
            "runtime_materialization_receipt_sha256": (
                self.runtime_materialization_receipt_sha256
            ),
            "qwen_selected_checkpoint_identity": (
                self.qwen_selected_checkpoint_identity
            ),
            "phobert_selected_checkpoint_identity": (
                self.phobert_selected_checkpoint_identity
            ),
            "phobert_selected_artifact_sha256": (
                self.phobert_selected_artifact_sha256
            ),
        }


def _require_sha256(value: object, *, where: str) -> str:
    if not isinstance(value, str) or not _SHA256_RE.fullmatch(value):
        raise Phase40ProductionAuthorityError(f"{where} must be lowercase SHA-256")
    return value


def _absolute(path: Path) -> Path:
    return Path(os.path.abspath(os.path.normpath(os.fspath(path))))


def _path_is_redirecting(path: Path) -> bool:
    try:
        metadata = os.lstat(path)
    except OSError as exc:
        raise Phase40ProductionAuthorityError(
            f"cannot inspect trusted path safely: {path}"
        ) from exc
    return bool(
        stat.S_ISLNK(metadata.st_mode)
        or int(getattr(metadata, "st_file_attributes", 0))
        & _WINDOWS_REPARSE_POINT
    )


def _trusted_root(path: Path, *, where: str) -> Path:
    supplied = Path(path)
    raw = os.fspath(supplied)
    if (
        not supplied.is_absolute()
        or "\x00" in raw
        or ".." in supplied.parts
    ):
        raise Phase40ProductionAuthorityError(
            f"{where} must be a canonical bounded absolute path"
        )
    root = _absolute(supplied)
    if root.parent == root or not root.is_dir():
        raise Phase40ProductionAuthorityError(
            f"{where} must be an existing bounded directory"
        )
    for component in reversed((root, *root.parents)):
        if _path_is_redirecting(component):
            raise Phase40ProductionAuthorityError(
                f"{where} ancestry must not contain a symlink or reparse point"
            )
    return root


def _require_disjoint(first: Path, second: Path, *, where: str) -> None:
    try:
        common = Path(os.path.commonpath((os.fspath(first), os.fspath(second))))
    except ValueError:
        # On Windows, roots on different volumes are necessarily disjoint.
        return
    if os.path.normcase(os.fspath(common)) in {
        os.path.normcase(os.fspath(first)),
        os.path.normcase(os.fspath(second)),
    }:
        raise Phase40ProductionAuthorityError(f"{where} trust roots must be disjoint")


def _fixed_file(root: Path, relative: PurePosixPath, *, where: str) -> Path:
    if relative.is_absolute() or ".." in relative.parts:
        raise AssertionError("code-fixed authority path must be bounded and relative")
    path = _absolute(root / relative)
    if path == root or root not in path.parents:
        raise Phase40ProductionAuthorityError(f"fixed {where} escaped its trust root")
    current = root
    for component in relative.parts:
        current /= component
        if not current.exists() and not current.is_symlink():
            raise Phase40ProductionAuthorityError(f"fixed {where} is missing")
        if _path_is_redirecting(current):
            raise Phase40ProductionAuthorityError(
                f"fixed {where} must not be a symlink or reparse point"
            )
    if not path.is_file():
        raise Phase40ProductionAuthorityError(f"fixed {where} must be a regular file")
    return path


def _strict_json_object(path: Path, *, where: str) -> dict[str, Any]:
    raw = path.read_bytes()

    def reject_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise Phase40ProductionAuthorityError(
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
        raise Phase40ProductionAuthorityError(
            f"{where} must be strict UTF-8 JSON"
        ) from exc
    if not isinstance(value, dict):
        raise Phase40ProductionAuthorityError(f"{where} must be a JSON object")
    return value


def _qwen_context(repo_root: Path) -> GGUFVerificationContext:
    receipt_path = _fixed_file(
        repo_root,
        QWEN_GGUF_VERIFICATION_RECEIPT_RELATIVE_PATH,
        where="Qwen GGUF verification receipt",
    )
    receipt = _strict_json_object(
        receipt_path,
        where="Qwen GGUF verification receipt",
    )
    upstream = receipt.get("upstream")
    selection = receipt.get("selection")
    if not isinstance(upstream, Mapping) or not isinstance(selection, Mapping):
        raise Phase40ProductionAuthorityError(
            "Qwen GGUF verification receipt authority fields are malformed"
        )
    checkpoint = selection.get("selected_checkpoint")
    if not isinstance(checkpoint, Mapping):
        raise Phase40ProductionAuthorityError(
            "Qwen GGUF verification receipt checkpoint is malformed"
        )
    final_authority_sha256 = _require_sha256(
        upstream.get("final_comparison_authority_sha256"),
        where="Qwen receipt final comparison authority",
    )
    origin_request_sha256 = _require_sha256(
        upstream.get("origin_request_sha256"),
        where="Qwen receipt origin request authority",
    )
    selected_run_id = selection.get("run_id")
    checkpoint_identity = checkpoint.get("artifact_identity")
    if not isinstance(selected_run_id, str) or not selected_run_id:
        raise Phase40ProductionAuthorityError("selected Qwen run ID is malformed")
    if not isinstance(checkpoint_identity, str):
        raise Phase40ProductionAuthorityError(
            "selected Qwen checkpoint identity is malformed"
        )
    return GGUFVerificationContext(
        final_comparison_authority_sha256=final_authority_sha256,
        origin_request_sha256=origin_request_sha256,
        selected_run_id=selected_run_id,
        selected_checkpoint_identity=checkpoint_identity,
    )


def _mapping_sha256(
    value: Mapping[str, Any],
    field: str,
    *,
    where: str,
) -> str:
    return _require_sha256(value.get(field), where=where)


def _runtime_materialization_receipt_sha256(
    receipt: object,
    runtime: object,
) -> str:
    """Bind the portable materialization receipt to the loaded runtime authority."""

    if not isinstance(receipt, Mapping):
        raise Phase40ProductionAuthorityError(
            "runtime materialization verifier returned a malformed authority"
        )
    authority = receipt.get("authority")
    runtime_sha256 = _require_sha256(
        getattr(runtime, "authority_sha256", None),
        where="runtime dependency byte authority",
    )
    if (
        not isinstance(authority, Mapping)
        or authority.get("authority_sha256") != runtime_sha256
    ):
        raise Phase40ProductionAuthorityError(
            "runtime materialization receipt binds a different runtime authority"
        )
    return _mapping_sha256(
        receipt,
        "receipt_sha256",
        where="runtime materialization receipt authority",
    )


def load_phase40_portable_production_authorities(
    *,
    repo_root: Path,
) -> VerifiedPhase40ProductionAuthorities:
    """Authenticate the fixed repository receipts without external model I/O.

    This is intentionally a *byte-authority* closure.  It proves that every
    portable receipt is canonical and self-hashed.  The launch, Qwen, and
    PhoBERT receipts bind the frozen final comparison authority; the runtime
    materialization receipt instead binds the runtime dependency authority.
    Stronger external GGUF/PhoBERT verification and live runtime recapture
    remain separate gates.
    """

    from src.model_adaptation import phase40_final_authority as final_authority

    repository = _trusted_root(repo_root, where="repository root")
    try:
        comparison = verify_phase40_comparison_launch_receipt(
            repo_root=repository
        )
        runtime_path = _fixed_file(
            repository,
            RUNTIME_DEPENDENCY_AUTHORITY_RELATIVE_PATH,
            where="runtime dependency authority",
        )
        runtime = load_runtime_dependency_authority(runtime_path)
        runtime_materialization = load_runtime_materialization_receipt(
            repo_root=repository
        )
        qwen = load_phase40_qwen_gguf_verification_receipt(
            repo_root=repository
        )
        qwen_context = _qwen_context(repository)
        phobert = load_phobert_release_receipt(repo_root=repository)
        final = final_authority.load_frozen_phase40_final_comparison_authority(
            repo_root=repository
        )
    except Exception as exc:
        raise Phase40ProductionAuthorityError(
            "portable production byte-authority verification failed"
        ) from exc

    if not isinstance(comparison, Mapping) or not isinstance(qwen, Mapping):
        raise Phase40ProductionAuthorityError(
            "portable production verifier returned a malformed authority"
        )
    qwen_selection = qwen.get("selection")
    if not isinstance(qwen_selection, Mapping):
        raise Phase40ProductionAuthorityError("verified Qwen selection is malformed")
    qwen_checkpoint_payload = qwen_selection.get("selected_checkpoint")
    if not isinstance(qwen_checkpoint_payload, Mapping):
        raise Phase40ProductionAuthorityError("verified Qwen checkpoint is malformed")
    qwen_checkpoint = qwen_checkpoint_payload.get("artifact_identity")
    if (
        not isinstance(qwen_checkpoint, str)
        or qwen_checkpoint != qwen_context.selected_checkpoint_identity
    ):
        raise Phase40ProductionAuthorityError(
            "portable Qwen receipt checkpoint identity drifted"
        )

    if qwen_context.final_comparison_authority_sha256 != final.authority_sha256:
        raise Phase40ProductionAuthorityError(
            "Qwen receipt binds a different final comparison authority"
        )
    qwen_resolution = final.by_run_id.get(final_authority.QWEN_QLORA_RUN_ID)
    phobert_resolution = final.by_run_id.get(
        final_authority.RECOVERY_PHOBERT_RUN_ID
    )
    if (
        qwen_resolution is None
        or phobert_resolution is None
        or qwen_context.origin_request_sha256
        != qwen_resolution.origin.request_sha256
    ):
        raise Phase40ProductionAuthorityError(
            "Qwen receipt origin differs from the final comparison authority"
        )

    phobert_upstream = getattr(phobert, "upstream", None)
    if not isinstance(phobert_upstream, Mapping):
        raise Phase40ProductionAuthorityError("PhoBERT receipt upstream is malformed")
    if (
        phobert_upstream.get("final_comparison_authority_sha256")
        != final.authority_sha256
        or phobert_upstream.get("origin_run_request_sha256")
        != phobert_resolution.origin.request_sha256
        or getattr(phobert, "selected_run_id", None)
        != final_authority.RECOVERY_PHOBERT_RUN_ID
    ):
        raise Phase40ProductionAuthorityError(
            "PhoBERT receipt origin differs from the final comparison authority"
        )
    phobert_checkpoint = getattr(phobert, "selected_checkpoint_identity", None)
    if not isinstance(phobert_checkpoint, str):
        raise Phase40ProductionAuthorityError(
            "verified PhoBERT checkpoint identity is malformed"
        )

    return VerifiedPhase40ProductionAuthorities(
        verification_mode=PORTABLE_RECEIPTS_ONLY,
        comparison_launch_receipt_sha256=_mapping_sha256(
            comparison,
            "receipt_sha256",
            where="comparison-launch receipt authority",
        ),
        qwen_gguf_verification_receipt_sha256=_mapping_sha256(
            qwen,
            "receipt_sha256",
            where="Qwen GGUF receipt authority",
        ),
        phobert_release_receipt_authority_sha256=_require_sha256(
            getattr(phobert, "authority_sha256", None),
            where="PhoBERT release receipt authority",
        ),
        phobert_segmenter_authority_sha256=_require_sha256(
            getattr(runtime, "segmenter_sha256", None),
            where="PhoBERT segmenter authority",
        ),
        runtime_dependency_authority_sha256=_require_sha256(
            getattr(runtime, "authority_sha256", None),
            where="runtime dependency byte authority",
        ),
        runtime_materialization_receipt_sha256=(
            _runtime_materialization_receipt_sha256(
                runtime_materialization,
                runtime,
            )
        ),
        qwen_selected_checkpoint_identity=qwen_checkpoint,
        phobert_selected_checkpoint_identity=phobert_checkpoint,
        phobert_selected_artifact_sha256=_require_sha256(
            getattr(phobert, "selected_artifact_sha256", None),
            where="selected PhoBERT artifact",
        ),
    )


def verify_phase40_production_authorities(
    *,
    repo_root: Path,
    qwen_export_root: Path,
    phobert_transfer_root: Path,
) -> VerifiedPhase40ProductionAuthorities:
    """Verify every code-fixed Phase 40 authority and return its typed closure.

    The trust roots are explicit because the Qwen export and PhoBERT release
    remain immutable in separate off-repository roots.  No descendant path is
    caller configurable.
    """

    repository = _trusted_root(repo_root, where="repository root")
    qwen_root = _trusted_root(qwen_export_root, where="Qwen export root")
    phobert_root = _trusted_root(
        phobert_transfer_root,
        where="PhoBERT transfer root",
    )
    _require_disjoint(repository, qwen_root, where="repository/Qwen")
    _require_disjoint(repository, phobert_root, where="repository/PhoBERT")
    _require_disjoint(qwen_root, phobert_root, where="Qwen/PhoBERT")

    try:
        comparison = verify_phase40_comparison_launch_receipt(
            repo_root=repository
        )
    except Exception as exc:
        raise Phase40ProductionAuthorityError(
            "comparison-launch authority verification failed"
        ) from exc
    if not isinstance(comparison, Mapping):
        raise Phase40ProductionAuthorityError(
            "comparison-launch verifier returned a malformed authority"
        )

    runtime_path = _fixed_file(
        repository,
        RUNTIME_DEPENDENCY_AUTHORITY_RELATIVE_PATH,
        where="runtime dependency authority",
    )
    try:
        runtime = load_runtime_dependency_authority(runtime_path)
        runtime_materialization = load_runtime_materialization_receipt(
            repo_root=repository
        )
    except Exception as exc:
        raise Phase40ProductionAuthorityError(
            "runtime dependency/materialization authority verification failed"
        ) from exc

    qwen_context = _qwen_context(repository)
    qwen_manifest_path = _fixed_file(
        qwen_root,
        QWEN_GGUF_EXPORT_MANIFEST_RELATIVE_PATH,
        where="Qwen GGUF export manifest",
    )
    try:
        qwen = verify_phase40_qwen_gguf_verification_receipt(
            repo_root=repository,
            export_manifest_path=qwen_manifest_path,
            context=qwen_context,
        )
    except Exception as exc:
        raise Phase40ProductionAuthorityError(
            "Qwen GGUF authority verification failed"
        ) from exc
    if not isinstance(qwen, Mapping):
        raise Phase40ProductionAuthorityError(
            "Qwen GGUF verifier returned a malformed authority"
        )
    selection = qwen.get("selection")
    if not isinstance(selection, Mapping):
        raise Phase40ProductionAuthorityError(
            "verified Qwen selection is malformed"
        )
    checkpoint = selection.get("selected_checkpoint")
    if not isinstance(checkpoint, Mapping):
        raise Phase40ProductionAuthorityError(
            "verified Qwen checkpoint is malformed"
        )
    qwen_checkpoint = checkpoint.get("artifact_identity")
    if (
        not isinstance(qwen_checkpoint, str)
        or qwen_checkpoint != qwen_context.selected_checkpoint_identity
    ):
        raise Phase40ProductionAuthorityError(
            "verified Qwen checkpoint differs from its fixed receipt context"
        )

    try:
        phobert = verify_phobert_release_bundle(
            repo_root=repository,
            transfer_root=phobert_root,
        )
    except Exception as exc:
        raise Phase40ProductionAuthorityError(
            "PhoBERT release authority verification failed"
        ) from exc
    receipt = getattr(phobert, "receipt", None)
    if receipt is None:
        raise Phase40ProductionAuthorityError(
            "PhoBERT release verifier returned a malformed authority"
        )
    phobert_checkpoint = getattr(receipt, "selected_checkpoint_identity", None)
    if not isinstance(phobert_checkpoint, str):
        raise Phase40ProductionAuthorityError(
            "verified PhoBERT checkpoint identity is malformed"
        )

    return VerifiedPhase40ProductionAuthorities(
        verification_mode=EXTERNAL_MODELS_PORTABLE_RUNTIME,
        comparison_launch_receipt_sha256=_mapping_sha256(
            comparison,
            "receipt_sha256",
            where="comparison-launch receipt authority",
        ),
        qwen_gguf_verification_receipt_sha256=_mapping_sha256(
            qwen,
            "receipt_sha256",
            where="Qwen GGUF receipt authority",
        ),
        phobert_release_receipt_authority_sha256=_require_sha256(
            getattr(receipt, "authority_sha256", None),
            where="PhoBERT release receipt authority",
        ),
        phobert_segmenter_authority_sha256=_require_sha256(
            getattr(runtime, "segmenter_sha256", None),
            where="PhoBERT segmenter authority",
        ),
        runtime_dependency_authority_sha256=_require_sha256(
            getattr(runtime, "authority_sha256", None),
            where="runtime dependency authority",
        ),
        runtime_materialization_receipt_sha256=(
            _runtime_materialization_receipt_sha256(
                runtime_materialization,
                runtime,
            )
        ),
        qwen_selected_checkpoint_identity=qwen_checkpoint,
        phobert_selected_checkpoint_identity=phobert_checkpoint,
        phobert_selected_artifact_sha256=_require_sha256(
            getattr(receipt, "selected_artifact_sha256", None),
            where="selected PhoBERT artifact",
        ),
    )


__all__ = [
    "COMPARISON_LAUNCH_RECEIPT_RELATIVE_PATH",
    "EXTERNAL_MODELS_PORTABLE_RUNTIME",
    "PORTABLE_RECEIPTS_ONLY",
    "Phase40ProductionAuthorityError",
    "QWEN_GGUF_EXPORT_MANIFEST_RELATIVE_PATH",
    "RUNTIME_DEPENDENCY_AUTHORITY_RELATIVE_PATH",
    "RUNTIME_MATERIALIZATION_RECEIPT_RELATIVE_PATH",
    "VerifiedPhase40ProductionAuthorities",
    "load_phase40_portable_production_authorities",
    "verify_phase40_production_authorities",
]
