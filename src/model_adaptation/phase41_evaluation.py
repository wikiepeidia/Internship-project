"""Fail-closed, one-shot two-model evaluation for the Phase 41 holdout.

Preparation treats the held-out identity as opaque metadata.  Only
``run_phase41_once`` is allowed to acquire the payload, and it durably spends
the content identity before doing so.  The module has no model-library import;
it accepts two already-loaded, protocol-bound predictors.
"""

from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import re
from typing import BinaryIO, Callable, Iterable, Iterator, Mapping, Sequence


LABEL_ORDER = (
    "bank_impersonation",
    "zalo_social_engineering",
    "task_scam",
    "benign",
)
RISKY_LABELS = LABEL_ORDER[:3]
PREDICTION_COLUMNS = LABEL_ORDER + ("invalid_output",)
DATASET_KEYS = frozenset(
    {
        "text",
        "label",
        "risk_tier",
        "suspicious_spans",
        "xai_explanation",
        "source",
        "seed_id",
    }
)
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
SAFE_ID_RE = re.compile(r"^[a-z0-9][a-z0-9._-]{0,95}$")
SAFE_PARSER_ERROR_RE = re.compile(r"^[a-z0-9][a-z0-9_]{0,63}$")
EXPLICIT_AUTHORIZATION_STATEMENT = (
    "I authorize this one-shot two-model held-out evaluation. The validation "
    "contingency is closed, and any claim or post-claim failure permanently "
    "spends this holdout for unbiased evaluation."
)

PREPARED_NAME = "evaluation-request.json"
AUTHORIZATION_NAME = "one-shot-authorization.json"
CLAIM_NAME = "one-shot-claim.json"
QWEN_PREDICTIONS_NAME = "qwen-predictions.jsonl"
PHOBERT_PREDICTIONS_NAME = "phobert-predictions.jsonl"
RESULTS_NAME = "results.json"
REPORT_NAME = "results.md"
TERMINAL_NAME = "terminal.json"
PREAUTHORIZATION_NAME = "preauthorization-receipt.json"
PROTOCOLS_NAME = "frozen-inference-protocols.json"
SOURCE_MANIFEST_NAME = "execution-source-manifest.json"
ACCESS_RECEIPT_NAME = "evaluation-access-receipt.json"
EVIDENCE_MANIFEST_NAME = "evidence-manifest.json"
DEPLOYMENT_DISPOSITION_NAME = "deployment-fit-disposition.json"

# One code-fixed, repository-local registry prevents replay when the same
# frozen bytes are copied to another path or evaluated under another output
# root in this checkout. Production must put the same SHA-keyed claim in
# protected persistence outside a mutable/copyable checkout. The public API
# intentionally does not accept a registry override.


@dataclass(frozen=True, slots=True)
class _TestRuntime:
    registry_root: Path
    event_sink: list[str] | None = None


_TEST_RUNTIME: ContextVar[_TestRuntime | None] = ContextVar(
    "phase41_test_runtime", default=None
)


@contextmanager
def _phase41_test_runtime(
    *, registry_root: Path, event_sink: list[str] | None = None
) -> Iterator[None]:
    """Private synthetic seam; production APIs expose no registry/opener override."""

    token = _TEST_RUNTIME.set(_TestRuntime(Path(registry_root), event_sink))
    try:
        yield
    finally:
        _TEST_RUNTIME.reset(token)


def _emit_test_event(name: str) -> None:
    runtime = _TEST_RUNTIME.get()
    if runtime is not None and runtime.event_sink is not None:
        runtime.event_sink.append(name)


def _claim_registry_root() -> Path:
    runtime = _TEST_RUNTIME.get()
    if runtime is not None:
        return runtime.registry_root
    program_data = os.environ.get("ProgramData")
    if not program_data or not os.path.isabs(program_data):
        raise ContractError("ProgramData identity is missing or unsafe")
    return Path(program_data) / "VNPhish" / "phase41-one-shot-claims"


class Phase41PrototypeError(RuntimeError):
    """Base error for the one-shot prototype."""


class ContractError(Phase41PrototypeError):
    """An immutable input or artifact violates the prototype contract."""


class AlreadySpentError(Phase41PrototypeError):
    """The durable one-shot claim already exists."""


class AuthorizationError(Phase41PrototypeError):
    """The explicit local authorization is absent or invalid."""


@dataclass(frozen=True, slots=True)
class ModelIdentity:
    role: str
    run_id: str
    model_family: str
    adaptation_mode: str
    artifact_sha256: str
    selected_checkpoint_identity: str

    def __post_init__(self) -> None:
        if self.role not in ("qwen", "phobert"):
            raise ContractError("model role must be qwen or phobert")
        if not SAFE_ID_RE.fullmatch(self.run_id):
            raise ContractError("model run_id is not a safe identifier")
        expected = {
            "qwen": ("qwen", "qlora"),
            "phobert": ("phobert", "classification_head"),
        }[self.role]
        if (self.model_family, self.adaptation_mode) != expected:
            raise ContractError("model family/adaptation mode differs from its fixed role")
        _require_sha256(self.artifact_sha256, "model artifact")
        checkpoint_prefix = (
            "adapter-state-sha256:"
            if self.role == "qwen"
            else "model-state-sha256:"
        )
        if not self.selected_checkpoint_identity.startswith(checkpoint_prefix):
            raise ContractError("selected checkpoint identity has the wrong model-family prefix")
        _require_sha256(
            self.selected_checkpoint_identity.removeprefix(checkpoint_prefix),
            "selected checkpoint",
        )

    def as_dict(self) -> dict[str, str]:
        return {
            "role": self.role,
            "run_id": self.run_id,
            "model_family": self.model_family,
            "adaptation_mode": self.adaptation_mode,
            "artifact_sha256": self.artifact_sha256,
            "selected_checkpoint_identity": self.selected_checkpoint_identity,
        }


@dataclass(frozen=True, slots=True)
class SplitIdentity:
    path: str
    records: int
    bytes: int
    sha256: str
    label_counts: tuple[tuple[str, int], ...]

    def __post_init__(self) -> None:
        if not isinstance(self.path, str) or not self.path.strip():
            raise ContractError("reserved split path must be non-empty")
        if not isinstance(self.records, int) or isinstance(self.records, bool) or self.records <= 0:
            raise ContractError("reserved split record count must be positive")
        if not isinstance(self.bytes, int) or isinstance(self.bytes, bool) or self.bytes <= 0:
            raise ContractError("reserved split byte count must be positive")
        _require_sha256(self.sha256, "reserved split")
        if tuple(label for label, _ in self.label_counts) != LABEL_ORDER:
            raise ContractError("reserved split label counts must follow the fixed label order")
        if any(
            not isinstance(count, int) or isinstance(count, bool) or count <= 0
            for _, count in self.label_counts
        ):
            raise ContractError("reserved split must have positive support for every label")
        if sum(count for _, count in self.label_counts) != self.records:
            raise ContractError("reserved split label counts do not sum to its record count")

    def as_dict(self) -> dict[str, object]:
        return {
            "path": self.path,
            "records": self.records,
            "bytes": self.bytes,
            "sha256": self.sha256,
            "label_counts": {label: count for label, count in self.label_counts},
        }


@dataclass(frozen=True, slots=True)
class InferenceRow:
    row_id: str
    sequence_index: int
    text: str


@dataclass(frozen=True, slots=True)
class InMemorySnapshot:
    """Immutable predictor view; gold labels are intentionally not exposed."""

    rows: tuple[InferenceRow, ...]


@dataclass(frozen=True, slots=True)
class Prediction:
    row_id: str
    predicted_state: str
    raw_output: str
    parser_error: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.row_id, str) or not self.row_id:
            raise ContractError("prediction row_id must be non-empty")
        if self.predicted_state not in PREDICTION_COLUMNS:
            raise ContractError("prediction state is outside the fixed output columns")
        if not isinstance(self.raw_output, str):
            raise ContractError("prediction raw_output must be a string")
        if self.parser_error is not None and not isinstance(self.parser_error, str):
            raise ContractError("prediction parser_error must be a string or null")
        if self.predicted_state == "invalid_output" and (
            not self.parser_error or not SAFE_PARSER_ERROR_RE.fullmatch(self.parser_error)
        ):
            raise ContractError("invalid_output predictions require a fixed safe parser-error code")
        if self.predicted_state != "invalid_output" and self.parser_error is not None:
            raise ContractError("valid predictions cannot carry a parser_error")


@dataclass(frozen=True, slots=True)
class _EvaluationRow:
    inference: InferenceRow
    source_row_sha256: str
    gold_label: str


@dataclass(frozen=True, slots=True)
class _LoadedSnapshot:
    predictor_view: InMemorySnapshot
    rows: tuple[_EvaluationRow, ...]
    payload_bytes: int


# Public names emphasize that these values are frozen metadata.  The aliases
# keep the small, independently reviewed prototype representation intact.
FrozenModelIdentity = ModelIdentity
OpaqueHeldOutAuthority = SplitIdentity


@dataclass(frozen=True, slots=True)
class PreparedPhase41Evaluation:
    path: Path
    prepared_sha256: str


@dataclass(frozen=True, slots=True)
class Phase41EvidenceManifest:
    path: Path
    status: str
    evidence_manifest_sha256: str
    artifacts: tuple[tuple[str, str], ...]


@dataclass(frozen=True, slots=True)
class DeploymentFitDisposition:
    choice: str
    selected_checkpoint_identities: tuple[str, str]

    def __post_init__(self) -> None:
        if self.choice not in {"deferred", "authorized_post_evaluation_fit"}:
            raise ContractError("deployment-fit choice is outside the fixed enum")
        if len(self.selected_checkpoint_identities) != 2:
            raise ContractError("deployment-fit disposition requires two checkpoints")
        prefixes = ("adapter-state-sha256:", "model-state-sha256:")
        for identity, prefix in zip(self.selected_checkpoint_identities, prefixes, strict=True):
            if not identity.startswith(prefix):
                raise ContractError("deployment-fit checkpoint identity/order drifted")
            _require_sha256(identity.removeprefix(prefix), "deployment-fit checkpoint")


SplitOpener = Callable[[Path], BinaryIO]
Predictor = Callable[[InMemorySnapshot], Sequence[Prediction]]
Clock = Callable[[], str]


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _require_sha256(value: object, description: str) -> str:
    if not isinstance(value, str) or not SHA256_RE.fullmatch(value):
        raise ContractError(f"{description} SHA-256 must be 64 lowercase hexadecimal characters")
    return value


def _canonical_json_bytes(value: object) -> bytes:
    return (
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _exclusive_write(path: Path, payload: bytes) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    flags |= getattr(os, "O_BINARY", 0)
    descriptor = os.open(path, flags, 0o600)
    try:
        with os.fdopen(descriptor, "wb", closefd=False) as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
    finally:
        os.close(descriptor)
    return path


def _reject_duplicate_keys(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ContractError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _reject_nonfinite_json(value: str) -> object:
    raise ContractError(f"non-finite JSON constant is forbidden: {value}")


def _parse_json_bytes(payload: bytes, description: str) -> dict[str, object]:
    try:
        text = payload.decode("utf-8", errors="strict")
        value = json.loads(
            text,
            object_pairs_hook=_reject_duplicate_keys,
            parse_constant=_reject_nonfinite_json,
        )
    except UnicodeDecodeError as exc:
        raise ContractError(f"{description} is not strict UTF-8") from exc
    except json.JSONDecodeError as exc:
        raise ContractError(f"{description} is not strict JSON") from exc
    if not isinstance(value, dict):
        raise ContractError(f"{description} must be one JSON object")
    return value


def _load_canonical_json(path: Path, description: str) -> tuple[dict[str, object], bytes]:
    candidate = Path(path)
    if not candidate.is_file() or candidate.is_symlink():
        raise ContractError(f"{description} is missing or unsafe")
    payload = candidate.read_bytes()
    value = _parse_json_bytes(payload, description)
    if payload != _canonical_json_bytes(value):
        raise ContractError(f"{description} is not canonical JSON")
    return value, payload


def _parse_models(raw: object) -> tuple[ModelIdentity, ModelIdentity]:
    if not isinstance(raw, list) or len(raw) != 2:
        raise ContractError("evaluation request must contain exactly two model identities")
    models: list[ModelIdentity] = []
    for item in raw:
        if not isinstance(item, dict):
            raise ContractError("model identity must be one object")
        expected_keys = {
            "role",
            "run_id",
            "model_family",
            "adaptation_mode",
            "artifact_sha256",
            "selected_checkpoint_identity",
        }
        if set(item) != expected_keys:
            raise ContractError("model identity fields differ from the fixed contract")
        models.append(ModelIdentity(**item))  # type: ignore[arg-type]
    if tuple(model.role for model in models) != ("qwen", "phobert"):
        raise ContractError("model identities must be ordered Qwen then PhoBERT")
    if len({model.run_id for model in models}) != 2:
        raise ContractError("model run IDs must be unique")
    return models[0], models[1]


def _parse_split_identity(raw: object) -> SplitIdentity:
    if not isinstance(raw, dict):
        raise ContractError("held-out identity must be one object")
    if set(raw) != {"path", "records", "bytes", "sha256", "label_counts"}:
        raise ContractError("held-out identity fields differ from the fixed contract")
    raw_counts = raw["label_counts"]
    if not isinstance(raw_counts, dict) or set(raw_counts) != set(LABEL_ORDER):
        raise ContractError("held-out label counts differ from the fixed label order")
    return SplitIdentity(
        path=raw["path"],  # type: ignore[arg-type]
        records=raw["records"],  # type: ignore[arg-type]
        bytes=raw["bytes"],  # type: ignore[arg-type]
        sha256=raw["sha256"],  # type: ignore[arg-type]
        label_counts=tuple((label, raw_counts[label]) for label in LABEL_ORDER),  # type: ignore[misc]
    )


def prepare_evaluation(
    output_root: Path,
    *,
    reserved_split_path: Path,
    expected_records: int,
    expected_bytes: int,
    expected_sha256: str,
    expected_label_counts: Mapping[str, int],
    models: Sequence[ModelIdentity],
    authorities: Mapping[str, object] | None = None,
    prepared_at_utc: str | None = None,
) -> Path:
    """Freeze PREPARED state without opening or inspecting the reserved split."""

    ordered_models = tuple(models)
    if len(ordered_models) != 2 or tuple(model.role for model in ordered_models) != (
        "qwen",
        "phobert",
    ):
        raise ContractError("PREPARED state requires exactly Qwen then PhoBERT")
    if len({model.run_id for model in ordered_models}) != 2:
        raise ContractError("PREPARED model run IDs must be unique")
    if set(expected_label_counts) != set(LABEL_ORDER):
        raise ContractError("expected label counts must contain exactly four labels")
    # Opaque by design: do not resolve, normalize, stat, hash, enumerate, or
    # open this declared path during preparation.
    split = SplitIdentity(
        path=os.fspath(reserved_split_path),
        records=expected_records,
        bytes=expected_bytes,
        sha256=expected_sha256,
        label_counts=tuple((label, expected_label_counts[label]) for label in LABEL_ORDER),
    )
    payload = {
        "schema_version": "phase41-one-shot-request-v1",
        "state": "prepared",
        "prepared_at_utc": prepared_at_utc or _utc_now(),
        "held_out": split.as_dict(),
        "models": [model.as_dict() for model in ordered_models],
        "authorities": dict(authorities or {}),
        "prediction_policy": {
            "qwen_retries": 0,
            "qwen_repairs": False,
            "phobert_decision": "fixed-four-logit-argmax",
        },
        "report_policy": {
            "terminal_evidence_only": True,
            "model_selection_after_test": False,
            "training_action_after_test": False,
        },
    }
    root = Path(output_root)
    root.mkdir(parents=True, exist_ok=True)
    return _exclusive_write(root / PREPARED_NAME, _canonical_json_bytes(payload))


def authorize_evaluation(
    output_root: Path,
    *,
    operator_id: str,
    statement: str,
    authorized_at_utc: str | None = None,
) -> Path:
    """Freeze an explicit, hash-bound local authorization; this is not a signature."""

    if statement != EXPLICIT_AUTHORIZATION_STATEMENT:
        raise AuthorizationError("authorization statement does not match the fixed acknowledgement")
    if not SAFE_ID_RE.fullmatch(operator_id):
        raise AuthorizationError("operator_id is not a safe identifier")
    root = Path(output_root)
    prepared, prepared_bytes = _load_canonical_json(
        root / PREPARED_NAME, "Phase 41 evaluation request"
    )
    _validate_prepared(prepared)
    payload = {
        "schema_version": "phase41-explicit-authorization-v1",
        "state": "explicitly_authorized",
        "authorization_method": "explicit_local_attestation",
        "operator_id": operator_id,
        "authorized_at_utc": authorized_at_utc or _utc_now(),
        "statement": statement,
        "prepared_sha256": _sha256(prepared_bytes),
    }
    try:
        return _exclusive_write(root / AUTHORIZATION_NAME, _canonical_json_bytes(payload))
    except FileExistsError as exc:
        raise AuthorizationError("explicit authorization already exists") from exc


def _validate_prepared(prepared: Mapping[str, object]) -> tuple[
    SplitIdentity, tuple[ModelIdentity, ModelIdentity]
]:
    if set(prepared) != {
        "schema_version",
        "state",
        "prepared_at_utc",
        "held_out",
        "models",
        "authorities",
        "prediction_policy",
        "report_policy",
    }:
        raise ContractError("evaluation request fields differ from the fixed contract")
    if (
        prepared["schema_version"] != "phase41-one-shot-request-v1"
        or prepared["state"] != "prepared"
    ):
        raise ContractError("evaluation request schema/state is invalid")
    if prepared["prediction_policy"] != {
        "qwen_retries": 0,
        "qwen_repairs": False,
        "phobert_decision": "fixed-four-logit-argmax",
    }:
        raise ContractError("prediction policy drifted")
    authorities = prepared["authorities"]
    if not isinstance(authorities, dict):
        raise ContractError("preauthorization authorities must be an object")
    if authorities:
        expected_authorities = {
            "protocols_sha256",
            "execution_source_manifest_sha256",
            "comparison_authority_sha256",
            "review_closure_sha256",
            "comparison_launch_receipt_sha256",
            "prior_human_exposure_disclosed",
        }
        if set(authorities) != expected_authorities:
            raise ContractError("preauthorization authority fields drifted")
        for name in expected_authorities - {"prior_human_exposure_disclosed"}:
            _require_sha256(authorities[name], name)
        if authorities["prior_human_exposure_disclosed"] is not True:
            raise ContractError("prior held-out human/content exposure must be disclosed")
    if prepared["report_policy"] != {
        "terminal_evidence_only": True,
        "model_selection_after_test": False,
        "training_action_after_test": False,
    }:
        raise ContractError("terminal report policy drifted")
    return _parse_split_identity(prepared["held_out"]), _parse_models(prepared["models"])


def _validate_authorization(
    authorization: Mapping[str, object], *, prepared_sha256: str
) -> None:
    if set(authorization) != {
        "schema_version",
        "state",
        "authorization_method",
        "operator_id",
        "authorized_at_utc",
        "statement",
        "prepared_sha256",
    }:
        raise AuthorizationError("authorization fields differ from the fixed contract")
    if (
        authorization["schema_version"] != "phase41-explicit-authorization-v1"
        or authorization["state"] != "explicitly_authorized"
        or authorization["authorization_method"] != "explicit_local_attestation"
        or authorization["statement"] != EXPLICIT_AUTHORIZATION_STATEMENT
        or authorization["prepared_sha256"] != prepared_sha256
    ):
        raise AuthorizationError("authorization does not bind the prepared request")
    if not isinstance(authorization["operator_id"], str) or not SAFE_ID_RE.fullmatch(
        authorization["operator_id"]
    ):
        raise AuthorizationError("authorization operator_id is invalid")


def _global_claim_path(identity: SplitIdentity) -> Path:
    """Return the one repository-local claim shared by every path/output root.

    The registry location is fixed by this module and the filename is derived
    only from the frozen split SHA-256. Computing it does not stat or open the
    split.
    """

    return _claim_registry_root() / f"{identity.sha256}.claim.json"


def _assert_unspent_and_clean(root: Path, global_claim: Path) -> None:
    local_claim = root / CLAIM_NAME
    if (
        local_claim.exists()
        or local_claim.is_symlink()
        or global_claim.exists()
        or global_claim.is_symlink()
    ):
        raise AlreadySpentError("the Phase 41 holdout already has a durable claim")
    for name in (
        QWEN_PREDICTIONS_NAME,
        PHOBERT_PREDICTIONS_NAME,
        RESULTS_NAME,
        REPORT_NAME,
        TERMINAL_NAME,
    ):
        candidate = root / name
        if candidate.exists() or candidate.is_symlink():
            raise ContractError(f"pre-claim output already exists: {name}")


def _claim_once(
    root: Path,
    *,
    identity: SplitIdentity,
    prepared_sha256: str,
    authorization_sha256: str,
    claimed_at_utc: str,
) -> tuple[Path, bytes]:
    payload = _canonical_json_bytes(
        {
            "schema_version": "phase41-one-shot-claim-v1",
            "state": "spent",
            "claimed_at_utc": claimed_at_utc,
            "prepared_sha256": prepared_sha256,
            "authorization_sha256": authorization_sha256,
            "reserved_split_sha256": identity.sha256,
            "reserved_split_path_sha256": _sha256(identity.path.encode("utf-8")),
            "meaning": "existence permanently blocks another governed evaluation attempt",
        }
    )
    global_path = _global_claim_path(identity)
    try:
        _exclusive_write(global_path, payload)
    except FileExistsError as exc:
        raise AlreadySpentError("the Phase 41 holdout was claimed concurrently") from exc
    # Keep an identical receipt with the result bundle. The global claim is
    # authoritative; failure to create the local receipt still leaves the
    # holdout permanently spent.
    _exclusive_write(root / CLAIM_NAME, payload)
    _emit_test_event("claim_durable")
    return global_path, payload


def _decode_split_rows(payload: bytes, identity: SplitIdentity) -> _LoadedSnapshot:
    if len(payload) != identity.bytes:
        raise ContractError(
            f"held-out byte count mismatch: expected {identity.bytes}, got {len(payload)}"
        )
    digest = _sha256(payload)
    if digest != identity.sha256:
        raise ContractError("held-out SHA-256 mismatch")
    try:
        text = payload.decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise ContractError("held-out payload is not strict UTF-8") from exc
    if "\r" in text:
        raise ContractError("held-out payload contains unsupported CR bytes")
    if not text:
        raise ContractError("held-out payload is empty")
    framed = text[:-1].split("\n") if text.endswith("\n") else text.split("\n")
    if not framed or any(not line for line in framed):
        raise ContractError("held-out payload contains a blank JSONL record")

    evaluation_rows: list[_EvaluationRow] = []
    support = {label: 0 for label in LABEL_ORDER}
    cursor = 0
    for index, line in enumerate(framed):
        line_bytes = line.encode("utf-8")
        raw = _parse_json_bytes(line_bytes, f"held-out record {index}")
        if set(raw) != DATASET_KEYS:
            raise ContractError("held-out record fields differ from the fixed dataset schema")
        text_value = raw["text"]
        label = raw["label"]
        if not isinstance(text_value, str) or not text_value:
            raise ContractError("held-out record text must be non-empty")
        if label not in LABEL_ORDER:
            raise ContractError("held-out record label is outside the fixed order")
        if not isinstance(raw["suspicious_spans"], list) or not all(
            isinstance(item, str) for item in raw["suspicious_spans"]
        ):
            raise ContractError("held-out suspicious_spans must be a string list")
        for field in ("risk_tier", "xai_explanation", "source", "seed_id"):
            if not isinstance(raw[field], str) or not raw[field]:
                raise ContractError(f"held-out {field} must be non-empty text")
        source_sha = _sha256(line_bytes)
        row_digest = hashlib.sha256(
            b"phase41-inference-row-v2\0"
            + str(index).encode("ascii")
            + b"\0"
            + text_value.encode("utf-8")
        ).hexdigest()
        inference = InferenceRow(
            row_id=f"p41-row-v2-{row_digest}",
            sequence_index=index,
            text=text_value,
        )
        evaluation_rows.append(
            _EvaluationRow(
                inference=inference,
                source_row_sha256=source_sha,
                gold_label=label,
            )
        )
        support[label] += 1
        cursor += len(line_bytes)
    if len(evaluation_rows) != identity.records:
        raise ContractError(
            f"held-out record count mismatch: expected {identity.records}, got {len(evaluation_rows)}"
        )
    if support != dict(identity.label_counts):
        raise ContractError("held-out label support differs from the prepared authority")
    public = InMemorySnapshot(rows=tuple(row.inference for row in evaluation_rows))
    return _LoadedSnapshot(public, tuple(evaluation_rows), len(payload))


def _open_snapshot_once(identity: SplitIdentity, opener: SplitOpener) -> _LoadedSnapshot:
    # This is the only reserved-split opener call in the prototype.
    handle = opener(Path(identity.path))
    _emit_test_event("handle_acquired")
    try:
        payload = handle.read()
        _emit_test_event("payload_read")
    finally:
        handle.close()
    if not isinstance(payload, bytes):
        raise ContractError("reserved split opener must return a binary stream")
    return _decode_split_rows(payload, identity)


def _validated_predictions(
    predictions: Sequence[Prediction],
    snapshot: InMemorySnapshot,
    *,
    role: str,
) -> tuple[Prediction, ...]:
    rows = tuple(predictions)
    if len(rows) != len(snapshot.rows):
        raise ContractError(f"{role} prediction count differs from the in-memory snapshot")
    for expected, prediction in zip(snapshot.rows, rows, strict=True):
        if not isinstance(prediction, Prediction):
            raise ContractError(f"{role} predictor returned a non-Prediction value")
        if prediction.row_id != expected.row_id:
            raise ContractError(f"{role} prediction order/identity differs from the snapshot")
    if len({row.row_id for row in rows}) != len(rows):
        raise ContractError(f"{role} predictions contain duplicate row IDs")
    return rows


def _safe_divide(numerator: int, denominator: int) -> float:
    return 0.0 if denominator == 0 else numerator / denominator


def compute_metrics(
    gold_labels: Sequence[str], predictions: Sequence[Prediction]
) -> dict[str, object]:
    gold = tuple(gold_labels)
    predicted = tuple(row.predicted_state for row in predictions)
    if not gold or len(gold) != len(predicted):
        raise ContractError("metrics require equal non-empty gold and prediction sequences")
    if any(label not in LABEL_ORDER for label in gold):
        raise ContractError("metric gold labels differ from the fixed label order")
    if any(label not in PREDICTION_COLUMNS for label in predicted):
        raise ContractError("metric predictions differ from the fixed output columns")

    matrix = [[0 for _ in PREDICTION_COLUMNS] for _ in LABEL_ORDER]
    for gold_label, predicted_label in zip(gold, predicted, strict=True):
        matrix[LABEL_ORDER.index(gold_label)][PREDICTION_COLUMNS.index(predicted_label)] += 1

    per_class: list[dict[str, object]] = []
    for label_index, label in enumerate(LABEL_ORDER):
        true_positive = matrix[label_index][label_index]
        support = sum(matrix[label_index])
        predicted_total = sum(row[label_index] for row in matrix)
        precision = _safe_divide(true_positive, predicted_total)
        recall = _safe_divide(true_positive, support)
        f1 = 0.0 if precision + recall == 0 else 2 * precision * recall / (precision + recall)
        per_class.append(
            {
                "label": label,
                "precision": precision,
                "recall": recall,
                "f1": f1,
                "support": support,
            }
        )

    evaluated_rows = len(gold)
    macro_f1 = sum(float(row["f1"]) for row in per_class) / len(LABEL_ORDER)
    weighted_f1 = sum(
        float(row["f1"]) * int(row["support"]) for row in per_class
    ) / evaluated_rows
    correct = sum(
        gold_label == predicted_label
        for gold_label, predicted_label in zip(gold, predicted, strict=True)
    )
    invalid_count = predicted.count("invalid_output")
    risky_to_benign = sum(
        gold_label in RISKY_LABELS and predicted_label == "benign"
        for gold_label, predicted_label in zip(gold, predicted, strict=True)
    )
    risky_to_invalid = sum(
        gold_label in RISKY_LABELS and predicted_label == "invalid_output"
        for gold_label, predicted_label in zip(gold, predicted, strict=True)
    )
    return {
        "label_order": list(LABEL_ORDER),
        "prediction_columns": list(PREDICTION_COLUMNS),
        "evaluated_rows": evaluated_rows,
        "per_class": per_class,
        "macro_f1": macro_f1,
        "weighted_f1": weighted_f1,
        "accuracy": correct / evaluated_rows,
        "confusion_matrix": matrix,
        "invalid_output_count": invalid_count,
        "invalid_output_rate": invalid_count / evaluated_rows,
        "risky_to_benign_count": risky_to_benign,
        "risky_to_invalid_count": risky_to_invalid,
    }


def _comparison_values(metrics: Mapping[str, object]) -> tuple[tuple[str, float, bool], ...]:
    values: list[tuple[str, float, bool]] = [
        ("macro_f1", float(metrics["macro_f1"]), True),
        ("weighted_f1", float(metrics["weighted_f1"]), True),
        ("accuracy", float(metrics["accuracy"]), True),
    ]
    per_class = metrics["per_class"]
    if not isinstance(per_class, list):
        raise ContractError("per_class metrics are malformed")
    for expected_label, raw in zip(LABEL_ORDER, per_class, strict=True):
        if not isinstance(raw, dict) or raw.get("label") != expected_label:
            raise ContractError("per_class metrics do not follow the fixed label order")
        for metric in ("precision", "recall", "f1"):
            values.append((f"{expected_label}.{metric}", float(raw[metric]), True))
    for metric in (
        "invalid_output_count",
        "risky_to_benign_count",
        "risky_to_invalid_count",
    ):
        values.append((f"{metric}(lower_is_better)", float(metrics[metric]), False))
    return tuple(values)


def comparison_statements(
    qwen_metrics: Mapping[str, object], phobert_metrics: Mapping[str, object]
) -> tuple[str, str, str]:
    qwen_values = _comparison_values(qwen_metrics)
    phobert_values = _comparison_values(phobert_metrics)
    phobert_higher: list[str] = []
    qwen_higher: list[str] = []
    ties: list[str] = []
    for (name, qwen, higher_is_better), (other_name, phobert, other_direction) in zip(
        qwen_values, phobert_values, strict=True
    ):
        if name != other_name or higher_is_better != other_direction:
            raise ContractError("metric comparison orders differ")
        if math.isclose(qwen, phobert, rel_tol=0.0, abs_tol=1e-12):
            ties.append(name)
        elif (phobert > qwen) == higher_is_better:
            phobert_higher.append(name)
        else:
            qwen_higher.append(name)

    def line(prefix: str, values: Sequence[str]) -> str:
        return f"{prefix}: {', '.join(values) if values else 'none'}."

    return (
        line("PhoBERT higher on", phobert_higher),
        line("Qwen higher on", qwen_higher),
        line("Ties", ties),
    )


def _prediction_jsonl(
    role: str,
    run_id: str,
    rows: Sequence[_EvaluationRow],
    predictions: Sequence[Prediction],
) -> bytes:
    chunks: list[bytes] = []
    for evaluation_row, prediction in zip(rows, predictions, strict=True):
        chunks.append(
            _canonical_json_bytes(
                {
                    "schema_version": "phase41-prediction-row-v1",
                    "model_role": role,
                    "model_run_id": run_id,
                    "row_id": prediction.row_id,
                    "sequence_index": evaluation_row.inference.sequence_index,
                    "source_row_sha256": evaluation_row.source_row_sha256,
                    "gold_label": evaluation_row.gold_label,
                    "predicted_state": prediction.predicted_state,
                    # Retain parser evidence without duplicating a model output
                    # that could echo the reserved message text.
                    "raw_output_bytes": len(prediction.raw_output.encode("utf-8")),
                    "raw_output_sha256": _sha256(prediction.raw_output.encode("utf-8")),
                    "parser_error": prediction.parser_error,
                }
            )
        )
    return b"".join(chunks)


def _render_report(result: Mapping[str, object]) -> bytes:
    models = result["models"]
    if not isinstance(models, list) or len(models) != 2:
        raise ContractError("result report requires exactly two models")
    lines = [
        "# Phase 41 One-Shot Two-Model Evaluation",
        "",
        "This artifact contains terminal descriptive measurements only.",
        "The partition had prior human/content exposure during corpus-quality review; this is one post-freeze model-evaluation pass, not a claim of human blindness.",
        "Poor results are terminal evidence and cannot trigger tuning, checkpoint selection, contingency activation, or dataset repair on this partition.",
        "",
    ]
    for model in models:
        if not isinstance(model, dict) or not isinstance(model.get("metrics"), dict):
            raise ContractError("result model entry is malformed")
        metrics = model["metrics"]
        lines.extend(
            [
                f"## {model['role']} ({model['run_id']})",
                "",
                f"- macro_f1: {float(metrics['macro_f1']):.6f}",
                f"- weighted_f1: {float(metrics['weighted_f1']):.6f}",
                f"- accuracy: {float(metrics['accuracy']):.6f}",
                f"- invalid_output_count: {metrics['invalid_output_count']}",
                f"- risky_to_benign_count: {metrics['risky_to_benign_count']}",
                f"- risky_to_invalid_count: {metrics['risky_to_invalid_count']}",
                "",
                "| label | precision | recall | f1 | support |",
                "|---|---:|---:|---:|---:|",
            ]
        )
        for row in metrics["per_class"]:
            lines.append(
                f"| {row['label']} | {float(row['precision']):.6f} | "
                f"{float(row['recall']):.6f} | {float(row['f1']):.6f} | {row['support']} |"
            )
        if metrics.get("label_order") != list(LABEL_ORDER):
            raise ContractError("report confusion matrix label order drifted")
        if metrics.get("prediction_columns") != list(PREDICTION_COLUMNS):
            raise ContractError("report confusion matrix prediction columns drifted")
        matrix = metrics.get("confusion_matrix")
        if not isinstance(matrix, list) or len(matrix) != len(LABEL_ORDER):
            raise ContractError("report confusion matrix row count is malformed")
        validated_matrix: list[list[int]] = []
        for row_index, raw_matrix_row in enumerate(matrix):
            if (
                not isinstance(raw_matrix_row, list)
                or len(raw_matrix_row) != len(PREDICTION_COLUMNS)
                or any(
                    not isinstance(value, int) or isinstance(value, bool) or value < 0
                    for value in raw_matrix_row
                )
            ):
                raise ContractError(
                    f"report confusion matrix row {row_index} is malformed"
                )
            validated_matrix.append(raw_matrix_row)
        lines.extend(
            [
                "",
                "### Confusion matrix",
                "",
                "Rows are gold labels; columns are predicted states.",
                "",
                "| gold label / predicted state | "
                + " | ".join(PREDICTION_COLUMNS)
                + " |",
                "|---|" + "---:|" * len(PREDICTION_COLUMNS),
            ]
        )
        for gold_label, matrix_row in zip(
            LABEL_ORDER, validated_matrix, strict=True
        ):
            lines.append(
                f"| {gold_label} | "
                + " | ".join(str(value) for value in matrix_row)
                + " |"
            )
        lines.append("")
    lines.extend(["## Plain comparison", ""])
    lines.extend(f"- {statement}" for statement in result["comparison_statements"])
    lines.append("")
    return ("\n".join(lines)).encode("utf-8")


def _terminal_failure(root: Path, claim_sha256: str, stage: str, exc: BaseException, clock: Clock) -> None:
    payload = {
        "schema_version": "phase41-terminal-v1",
        "status": "spent_failed",
        "completed_at_utc": clock(),
        "claim_sha256": claim_sha256,
        "failure_stage": stage,
        "error_type": type(exc).__name__,
        "rerun_permitted": False,
    }
    try:
        _exclusive_write(root / TERMINAL_NAME, _canonical_json_bytes(payload))
    except FileExistsError:
        # The claim still proves the holdout is spent. Never remove it to make
        # a failed attempt look rerunnable.
        pass


def run_once(
    output_root: Path,
    *,
    opener: SplitOpener,
    qwen_predictor: Predictor,
    phobert_predictor: Predictor,
    clock: Clock = _utc_now,
) -> dict[str, object]:
    """Consume authorization and permanently spend the holdout.

    Predictors must already be loaded, identity-checked, and smoke-tested by the
    caller before entry. Model loading inside either callback is a contract
    violation because a load failure would needlessly spend the one-shot run.
    """

    root = Path(output_root)
    prepared, prepared_bytes = _load_canonical_json(
        root / PREPARED_NAME, "Phase 41 evaluation request"
    )
    identity, models = _validate_prepared(prepared)
    authorization, authorization_bytes = _load_canonical_json(
        root / AUTHORIZATION_NAME, "Phase 41 explicit authorization"
    )
    prepared_sha = _sha256(prepared_bytes)
    authorization_sha = _sha256(authorization_bytes)
    _validate_authorization(authorization, prepared_sha256=prepared_sha)
    global_claim = _global_claim_path(identity)
    _assert_unspent_and_clean(root, global_claim)
    _, claim_bytes = _claim_once(
        root,
        identity=identity,
        prepared_sha256=prepared_sha,
        authorization_sha256=authorization_sha,
        claimed_at_utc=clock(),
    )
    claim_sha = _sha256(claim_bytes)
    stage = "open_reserved_split"
    try:
        # Recheck the authority bytes after the durable claim and before the
        # sole opener, closing the mutation window without making a data read.
        if (root / PREPARED_NAME).read_bytes() != prepared_bytes:
            raise ContractError("prepared request changed after the durable claim")
        if (root / AUTHORIZATION_NAME).read_bytes() != authorization_bytes:
            raise ContractError("authorization changed after the durable claim")
        loaded = _open_snapshot_once(identity, opener)

        stage = "qwen_prediction"
        qwen_predictions = _validated_predictions(
            qwen_predictor(loaded.predictor_view),
            loaded.predictor_view,
            role="qwen",
        )
        stage = "phobert_prediction"
        phobert_predictions = _validated_predictions(
            phobert_predictor(loaded.predictor_view),
            loaded.predictor_view,
            role="phobert",
        )
        gold = tuple(row.gold_label for row in loaded.rows)
        qwen_metrics = compute_metrics(gold, qwen_predictions)
        phobert_metrics = compute_metrics(gold, phobert_predictions)
        statements = comparison_statements(qwen_metrics, phobert_metrics)

        stage = "freeze_outputs"
        qwen_bytes = _prediction_jsonl(
            "qwen", models[0].run_id, loaded.rows, qwen_predictions
        )
        phobert_bytes = _prediction_jsonl(
            "phobert", models[1].run_id, loaded.rows, phobert_predictions
        )
        _exclusive_write(root / QWEN_PREDICTIONS_NAME, qwen_bytes)
        _exclusive_write(root / PHOBERT_PREDICTIONS_NAME, phobert_bytes)
        result: dict[str, object] = {
            "schema_version": "phase41-one-shot-results-v1",
            "status": "completed",
            "prepared_sha256": prepared_sha,
            "authorization_sha256": authorization_sha,
            "claim_sha256": claim_sha,
            "held_out": {
                "records": len(loaded.rows),
                "bytes": loaded.payload_bytes,
                "sha256": identity.sha256,
            },
            "prior_exposure": {
                "human_content_exposure_disclosed": prepared["authorities"].get(
                    "prior_human_exposure_disclosed", False
                ),
                "claim": "one_post_freeze_model_evaluation_pass",
            },
            "models": [
                {
                    "role": models[0].role,
                    "run_id": models[0].run_id,
                    "artifact_sha256": models[0].artifact_sha256,
                    "selected_checkpoint_identity": models[0].selected_checkpoint_identity,
                    "predictions_sha256": _sha256(qwen_bytes),
                    "metrics": qwen_metrics,
                },
                {
                    "role": models[1].role,
                    "run_id": models[1].run_id,
                    "artifact_sha256": models[1].artifact_sha256,
                    "selected_checkpoint_identity": models[1].selected_checkpoint_identity,
                    "predictions_sha256": _sha256(phobert_bytes),
                    "metrics": phobert_metrics,
                },
            ],
            "comparison_statements": list(statements),
            "terminal_policy": {
                "rerun_permitted": False,
                "test_driven_training_action_permitted": False,
                "test_driven_checkpoint_selection_permitted": False,
                "test_driven_dataset_repair_permitted": False,
                "test_driven_contingency_activation_permitted": False,
            },
        }
        result_bytes = _canonical_json_bytes(result)
        report_bytes = _render_report(result)
        _exclusive_write(root / RESULTS_NAME, result_bytes)
        _exclusive_write(root / REPORT_NAME, report_bytes)
        terminal = {
            "schema_version": "phase41-terminal-v1",
            "status": "completed",
            "completed_at_utc": clock(),
            "claim_sha256": claim_sha,
            "results_sha256": _sha256(result_bytes),
            "report_sha256": _sha256(report_bytes),
            "qwen_predictions_sha256": _sha256(qwen_bytes),
            "phobert_predictions_sha256": _sha256(phobert_bytes),
            "rerun_permitted": False,
        }
        _exclusive_write(root / TERMINAL_NAME, _canonical_json_bytes(terminal))
        return result
    except BaseException as exc:
        _terminal_failure(root, claim_sha, stage, exc, clock)
        raise


def _load_prediction_rows(
    path: Path, *, expected_role: str, expected_run_id: str
) -> tuple[list[str], list[str], tuple[Prediction, ...], bytes]:
    if not path.is_file() or path.is_symlink():
        raise ContractError(f"{expected_role} prediction artifact is missing or unsafe")
    payload = path.read_bytes()
    if not payload or not payload.endswith(b"\n"):
        raise ContractError(f"{expected_role} prediction artifact is partial or empty")
    gold: list[str] = []
    source_hashes: list[str] = []
    predictions: list[Prediction] = []
    for index, line in enumerate(payload.splitlines(keepends=True)):
        value = _parse_json_bytes(line, f"{expected_role} prediction row {index}")
        if line != _canonical_json_bytes(value):
            raise ContractError(f"{expected_role} prediction row is not canonical")
        expected_keys = {
            "schema_version",
            "model_role",
            "model_run_id",
            "row_id",
            "sequence_index",
            "source_row_sha256",
            "gold_label",
            "predicted_state",
            "raw_output_bytes",
            "raw_output_sha256",
            "parser_error",
        }
        if set(value) != expected_keys:
            raise ContractError(f"{expected_role} prediction fields drifted")
        if (
            value["schema_version"] != "phase41-prediction-row-v1"
            or value["model_role"] != expected_role
            or value["model_run_id"] != expected_run_id
            or value["sequence_index"] != index
        ):
            raise ContractError(f"{expected_role} prediction provenance/order drifted")
        _require_sha256(value["source_row_sha256"], "prediction source row")
        _require_sha256(value["raw_output_sha256"], "prediction raw output")
        if (
            not isinstance(value["raw_output_bytes"], int)
            or isinstance(value["raw_output_bytes"], bool)
            or value["raw_output_bytes"] < 0
        ):
            raise ContractError("prediction raw-output byte count is invalid")
        if value["gold_label"] not in LABEL_ORDER:
            raise ContractError("prediction gold label is outside the fixed order")
        gold.append(value["gold_label"])
        source_hashes.append(value["source_row_sha256"])
        predictions.append(
            Prediction(
                row_id=value["row_id"],
                predicted_state=value["predicted_state"],
                # verify_only needs the parsed state, not the sensitive raw
                # output. Its retained hash/length remain terminal evidence.
                raw_output="",
                parser_error=value["parser_error"],
            )
        )
    return gold, source_hashes, tuple(predictions), payload


def verify_only(output_root: Path) -> dict[str, object]:
    """Verify frozen results without accepting an opener or loading a model."""

    root = Path(output_root)
    prepared, prepared_bytes = _load_canonical_json(
        root / PREPARED_NAME, "Phase 41 evaluation request"
    )
    identity, models = _validate_prepared(prepared)
    authorization, authorization_bytes = _load_canonical_json(
        root / AUTHORIZATION_NAME, "Phase 41 explicit authorization"
    )
    prepared_sha = _sha256(prepared_bytes)
    authorization_sha = _sha256(authorization_bytes)
    _validate_authorization(authorization, prepared_sha256=prepared_sha)
    claim, claim_bytes = _load_canonical_json(root / CLAIM_NAME, "Phase 41 claim")
    global_claim, global_claim_bytes = _load_canonical_json(
        _global_claim_path(identity), "Phase 41 machine-local global claim"
    )
    if global_claim != claim or global_claim_bytes != claim_bytes:
        raise ContractError("local and global one-shot claims differ")
    if set(claim) != {
        "schema_version",
        "state",
        "claimed_at_utc",
        "prepared_sha256",
        "authorization_sha256",
        "reserved_split_sha256",
        "reserved_split_path_sha256",
        "meaning",
    } or (
        claim["schema_version"] != "phase41-one-shot-claim-v1"
        or claim["state"] != "spent"
        or not isinstance(claim["claimed_at_utc"], str)
        or not claim["claimed_at_utc"]
        or claim["prepared_sha256"] != prepared_sha
        or claim["authorization_sha256"] != authorization_sha
        or claim["reserved_split_sha256"] != identity.sha256
        or claim["reserved_split_path_sha256"]
        != _sha256(identity.path.encode("utf-8"))
        or claim["meaning"]
        != "existence permanently blocks another governed evaluation attempt"
    ):
        raise ContractError("durable claim differs from its authorities")
    claim_sha = _sha256(claim_bytes)
    terminal, _ = _load_canonical_json(root / TERMINAL_NAME, "Phase 41 terminal record")
    if set(terminal) != {
        "schema_version",
        "status",
        "completed_at_utc",
        "claim_sha256",
        "results_sha256",
        "report_sha256",
        "qwen_predictions_sha256",
        "phobert_predictions_sha256",
        "rerun_permitted",
    } or (
        terminal["schema_version"] != "phase41-terminal-v1"
        or terminal["status"] != "completed"
        or not isinstance(terminal["completed_at_utc"], str)
        or not terminal["completed_at_utc"]
        or terminal["claim_sha256"] != claim_sha
        or terminal["rerun_permitted"] is not False
    ):
        raise ContractError("Phase 41 evaluation is not terminal-complete")

    q_gold, q_sources, q_predictions, q_bytes = _load_prediction_rows(
        root / QWEN_PREDICTIONS_NAME,
        expected_role="qwen",
        expected_run_id=models[0].run_id,
    )
    p_gold, p_sources, p_predictions, p_bytes = _load_prediction_rows(
        root / PHOBERT_PREDICTIONS_NAME,
        expected_role="phobert",
        expected_run_id=models[1].run_id,
    )
    if (
        q_gold != p_gold
        or q_sources != p_sources
        or tuple(row.row_id for row in q_predictions)
        != tuple(row.row_id for row in p_predictions)
        or len(q_gold) != identity.records
    ):
        raise ContractError("the two prediction artifacts do not share one frozen cohort")
    retained_support = {label: q_gold.count(label) for label in LABEL_ORDER}
    if retained_support != dict(identity.label_counts):
        raise ContractError("retained prediction gold-label support differs from authority")
    if terminal.get("qwen_predictions_sha256") != _sha256(q_bytes) or terminal.get(
        "phobert_predictions_sha256"
    ) != _sha256(p_bytes):
        raise ContractError("prediction artifact hash differs from terminal evidence")

    result, result_bytes = _load_canonical_json(root / RESULTS_NAME, "Phase 41 results")
    if terminal.get("results_sha256") != _sha256(result_bytes):
        raise ContractError("result hash differs from terminal evidence")
    if set(result) != {
        "schema_version",
        "status",
        "prepared_sha256",
        "authorization_sha256",
        "claim_sha256",
        "held_out",
        "prior_exposure",
        "models",
        "comparison_statements",
        "terminal_policy",
    } or (
        result["schema_version"] != "phase41-one-shot-results-v1"
        or result["status"] != "completed"
        or result["prepared_sha256"] != prepared_sha
        or result["authorization_sha256"] != authorization_sha
        or result["claim_sha256"] != claim_sha
    ):
        raise ContractError("result authority fields drifted")
    if result["held_out"] != {
        "records": identity.records,
        "bytes": identity.bytes,
        "sha256": identity.sha256,
    }:
        raise ContractError("result held-out identity drifted")
    if result["prior_exposure"] != {
        "human_content_exposure_disclosed": True,
        "claim": "one_post_freeze_model_evaluation_pass",
    }:
        raise ContractError("prior-exposure disclosure drifted")
    result_models = result.get("models")
    if not isinstance(result_models, list) or len(result_models) != 2:
        raise ContractError("results must contain exactly two model rows")
    q_metrics = compute_metrics(q_gold, q_predictions)
    p_metrics = compute_metrics(p_gold, p_predictions)
    expected_metrics = (q_metrics, p_metrics)
    for model, expected_identity, expected_metric, predictions_sha in zip(
        result_models,
        models,
        expected_metrics,
        (_sha256(q_bytes), _sha256(p_bytes)),
        strict=True,
    ):
        if not isinstance(model, dict):
            raise ContractError("result model row is malformed")
        if set(model) != {
            "role",
            "run_id",
            "artifact_sha256",
            "selected_checkpoint_identity",
            "predictions_sha256",
            "metrics",
        } or (
            model["role"] != expected_identity.role
            or model["run_id"] != expected_identity.run_id
            or model["artifact_sha256"] != expected_identity.artifact_sha256
            or model["selected_checkpoint_identity"]
            != expected_identity.selected_checkpoint_identity
            or model["predictions_sha256"] != predictions_sha
            or model["metrics"] != expected_metric
        ):
            raise ContractError("result model identity or metrics drifted")
    expected_statements = list(comparison_statements(q_metrics, p_metrics))
    if result.get("comparison_statements") != expected_statements:
        raise ContractError("plain comparison statements drifted")
    if result.get("terminal_policy") != {
        "rerun_permitted": False,
        "test_driven_training_action_permitted": False,
        "test_driven_checkpoint_selection_permitted": False,
        "test_driven_dataset_repair_permitted": False,
        "test_driven_contingency_activation_permitted": False,
    }:
        raise ContractError("terminal result policy drifted")
    report_path = root / REPORT_NAME
    if not report_path.is_file() or report_path.is_symlink():
        raise ContractError("Phase 41 Markdown report is missing or unsafe")
    report_bytes = report_path.read_bytes()
    if terminal.get("report_sha256") != _sha256(report_bytes):
        raise ContractError("report hash differs from terminal evidence")
    if report_bytes != _render_report(result):
        raise ContractError("Markdown report differs from the canonical result")
    return result


def _write_source_manifest(output_root: Path, declared_tree_sha256: str) -> tuple[Path, str]:
    _require_sha256(declared_tree_sha256, "execution source tree")
    payload = _canonical_json_bytes(
        {
            "schema_version": "phase41-execution-source-manifest-v1",
            "declared_source_tree_sha256": declared_tree_sha256,
            "closed_import_roots": [
                "src.model_adaptation.phase41_evaluation",
                "src.model_adaptation.phase41_protocols",
                "src.model_adaptation.cli",
            ],
            "alternate_evaluators_permitted": False,
        }
    )
    path = _exclusive_write(Path(output_root) / SOURCE_MANIFEST_NAME, payload)
    return path, _sha256(payload)


def prepare_phase41_evaluation(
    output_root: Path,
    *,
    held_out: OpaqueHeldOutAuthority,
    models: Sequence[FrozenModelIdentity],
    protocols,  # Phase41ProtocolAuthority; kept lazy to avoid a module cycle
    comparison_authority_sha256: str,
    review_closure_sha256: str,
    comparison_launch_receipt_sha256: str,
    execution_source_manifest_sha256: str,
    prior_human_exposure_disclosed: bool,
) -> PreparedPhase41Evaluation:
    """Freeze preauthorization without performing any operation on ``held_out.path``."""

    from src.model_adaptation.phase41_protocols import (
        Phase41ProtocolAuthority,
        write_protocol_authority,
    )

    if not isinstance(held_out, SplitIdentity):
        raise ContractError("held-out authority must be OpaqueHeldOutAuthority")
    ordered_models = tuple(models)
    if len(ordered_models) != 2 or tuple(model.role for model in ordered_models) != (
        "qwen",
        "phobert",
    ):
        raise ContractError("model identities must be Qwen then PhoBERT")
    if not isinstance(protocols, Phase41ProtocolAuthority):
        raise ContractError("protocol authority type is invalid")
    if (
        protocols.qwen.body["adapter_checkpoint_identity"]
        != ordered_models[0].selected_checkpoint_identity
        or protocols.phobert.body["classifier_checkpoint_identity"]
        != ordered_models[1].selected_checkpoint_identity
    ):
        raise ContractError("protocol checkpoint identities differ from selected models")
    if prior_human_exposure_disclosed is not True:
        raise ContractError("prior human/content exposure disclosure is mandatory")

    root = Path(output_root)
    protocol_path = write_protocol_authority(root, protocols)
    protocol_bytes = protocol_path.read_bytes()
    _, source_manifest_sha = _write_source_manifest(
        root, execution_source_manifest_sha256
    )
    authorities = {
        "protocols_sha256": _sha256(protocol_bytes),
        "execution_source_manifest_sha256": source_manifest_sha,
        "comparison_authority_sha256": _require_sha256(
            comparison_authority_sha256, "comparison authority"
        ),
        "review_closure_sha256": _require_sha256(review_closure_sha256, "review closure"),
        "comparison_launch_receipt_sha256": _require_sha256(
            comparison_launch_receipt_sha256, "comparison launch receipt"
        ),
        "prior_human_exposure_disclosed": True,
    }
    request_path = prepare_evaluation(
        root,
        reserved_split_path=Path(held_out.path),
        expected_records=held_out.records,
        expected_bytes=held_out.bytes,
        expected_sha256=held_out.sha256,
        expected_label_counts=dict(held_out.label_counts),
        models=ordered_models,
        authorities=authorities,
    )
    request_bytes = request_path.read_bytes()
    prepared_sha = _sha256(request_bytes)
    preauthorization = _canonical_json_bytes(
        {
            "schema_version": "phase41-preauthorization-receipt-v1",
            "state": "prepared",
            "prepared_sha256": prepared_sha,
            "protocols_sha256": authorities["protocols_sha256"],
            "execution_source_manifest_sha256": source_manifest_sha,
            "comparison_authority_sha256": authorities["comparison_authority_sha256"],
            "review_closure_sha256": authorities["review_closure_sha256"],
            "comparison_launch_receipt_sha256": authorities[
                "comparison_launch_receipt_sha256"
            ],
            "models_ready_before_claim_required": True,
            "validation_contingency_closed_required": True,
        }
    )
    _exclusive_write(root / PREAUTHORIZATION_NAME, preauthorization)
    return PreparedPhase41Evaluation(request_path, prepared_sha)


def verify_phase41_preauthorization(output_root: Path) -> PreparedPhase41Evaluation:
    """Verify preauthorization artifacts without accepting or touching a split path."""

    from src.model_adaptation.phase41_protocols import load_protocol_authority

    root = Path(output_root)
    request, request_bytes = _load_canonical_json(
        root / PREPARED_NAME, "Phase 41 evaluation request"
    )
    _validate_prepared(request)
    protocols = load_protocol_authority(root)
    protocol_bytes = (root / PROTOCOLS_NAME).read_bytes()
    source, source_bytes = _load_canonical_json(
        root / SOURCE_MANIFEST_NAME, "Phase 41 execution source manifest"
    )
    if set(source) != {
        "schema_version",
        "declared_source_tree_sha256",
        "closed_import_roots",
        "alternate_evaluators_permitted",
    } or source["schema_version"] != "phase41-execution-source-manifest-v1":
        raise ContractError("execution source manifest fields drifted")
    _require_sha256(source["declared_source_tree_sha256"], "execution source tree")
    if source["alternate_evaluators_permitted"] is not False:
        raise ContractError("execution source permits an alternate evaluator")
    authorities = request["authorities"]
    assert isinstance(authorities, dict)
    if authorities["protocols_sha256"] != _sha256(protocol_bytes):
        raise ContractError("protocol artifact hash differs from request")
    if authorities["execution_source_manifest_sha256"] != _sha256(source_bytes):
        raise ContractError("execution source manifest hash differs from request")
    models = _parse_models(request["models"])
    if (
        protocols.qwen.body["adapter_checkpoint_identity"]
        != models[0].selected_checkpoint_identity
        or protocols.phobert.body["classifier_checkpoint_identity"]
        != models[1].selected_checkpoint_identity
    ):
        raise ContractError("protocol/model checkpoint binding drifted")
    receipt, _ = _load_canonical_json(
        root / PREAUTHORIZATION_NAME, "Phase 41 preauthorization receipt"
    )
    expected_receipt = {
        "schema_version": "phase41-preauthorization-receipt-v1",
        "state": "prepared",
        "prepared_sha256": _sha256(request_bytes),
        "protocols_sha256": authorities["protocols_sha256"],
        "execution_source_manifest_sha256": authorities[
            "execution_source_manifest_sha256"
        ],
        "comparison_authority_sha256": authorities["comparison_authority_sha256"],
        "review_closure_sha256": authorities["review_closure_sha256"],
        "comparison_launch_receipt_sha256": authorities[
            "comparison_launch_receipt_sha256"
        ],
        "models_ready_before_claim_required": True,
        "validation_contingency_closed_required": True,
    }
    if receipt != expected_receipt:
        raise ContractError("preauthorization receipt drifted")
    return PreparedPhase41Evaluation(root / PREPARED_NAME, _sha256(request_bytes))


def authorize_phase41_evaluation(
    output_root: Path,
    *,
    prepared_sha256: str,
    statement: str,
) -> Path:
    verified = verify_phase41_preauthorization(output_root)
    if prepared_sha256 != verified.prepared_sha256:
        raise AuthorizationError("authorization does not name the prepared request")
    return authorize_evaluation(
        output_root,
        operator_id="local-operator",
        statement=statement,
    )


def _owned_split_opener(path: Path) -> BinaryIO:
    """Sole production opener.  Task 2 replaces this with the Win32 handle owner."""

    return path.open("rb")


def _artifact_hashes(root: Path, names: Sequence[str]) -> tuple[tuple[str, str], ...]:
    hashes: list[tuple[str, str]] = []
    for name in names:
        candidate = root / name
        if not candidate.is_file() or candidate.is_symlink():
            raise ContractError(f"evidence artifact is missing or unsafe: {name}")
        hashes.append((name, _sha256(candidate.read_bytes())))
    return tuple(hashes)


def _manifest_from_disk(root: Path) -> Phase41EvidenceManifest:
    raw, payload = _load_canonical_json(
        root / EVIDENCE_MANIFEST_NAME, "Phase 41 evidence manifest"
    )
    if set(raw) != {"schema_version", "status", "artifacts", "terminal_policy"}:
        raise ContractError("evidence manifest fields drifted")
    if (
        raw["schema_version"] != "phase41-evidence-manifest-v1"
        or raw["status"] != "completed"
        or raw["terminal_policy"]
        != {
            "rerun_permitted": False,
            "test_outcome_used_for_tuning": False,
            "unbiased_test_score_claim_after_deployment_fit": False,
        }
    ):
        raise ContractError("evidence manifest terminal policy drifted")
    artifacts = raw["artifacts"]
    if not isinstance(artifacts, list):
        raise ContractError("evidence manifest artifacts must be a list")
    parsed: list[tuple[str, str]] = []
    for item in artifacts:
        if not isinstance(item, dict) or set(item) != {"name", "sha256"}:
            raise ContractError("evidence manifest artifact row drifted")
        if not isinstance(item["name"], str):
            raise ContractError("evidence artifact name is invalid")
        parsed.append((item["name"], _require_sha256(item["sha256"], "evidence artifact")))
    return Phase41EvidenceManifest(
        root / EVIDENCE_MANIFEST_NAME,
        "completed",
        _sha256(payload),
        tuple(parsed),
    )


def run_phase41_once(output_root: Path, qwen, phobert) -> Phase41EvidenceManifest:  # noqa: ANN001
    """Spend the authorization exactly once using two preloaded frozen predictors."""

    from src.model_adaptation.phase41_protocols import (
        FrozenPhoBertPredictor,
        FrozenQwenPredictor,
        load_protocol_authority,
    )

    root = Path(output_root)
    verify_phase41_preauthorization(root)
    if not isinstance(qwen, FrozenQwenPredictor) or not isinstance(
        phobert, FrozenPhoBertPredictor
    ):
        raise ContractError("run-once requires preloaded frozen Qwen and PhoBERT predictors")
    protocols = load_protocol_authority(root)
    if (
        qwen.protocol.protocol_sha256 != protocols.qwen.protocol_sha256
        or phobert.protocol.protocol_sha256 != protocols.phobert.protocol_sha256
    ):
        raise ContractError("predictor protocol identity drifted")
    result = run_once(
        root,
        opener=_owned_split_opener,
        qwen_predictor=qwen,
        phobert_predictor=phobert,
    )
    request, _ = _load_canonical_json(root / PREPARED_NAME, "Phase 41 request")
    identity, _ = _validate_prepared(request)
    claim_bytes = (root / CLAIM_NAME).read_bytes()
    access = _canonical_json_bytes(
        {
            "schema_version": "phase41-evaluation-access-v1",
            "claim_sha256": _sha256(claim_bytes),
            "requested_path_sha256": _sha256(identity.path.encode("utf-8")),
            "final_path_sha256": _sha256(identity.path.encode("utf-8")),
            "handle_acquisitions": 1,
            "sequential_payload_reads": 1,
            "observed_bytes": identity.bytes,
            "observed_sha256": identity.sha256,
            "observed_records": identity.records,
            "observed_label_counts": dict(identity.label_counts),
            "raw_content_retained": False,
        }
    )
    _exclusive_write(root / ACCESS_RECEIPT_NAME, access)
    if result.get("status") != "completed":
        raise ContractError("run-once did not produce completed results")
    artifact_names = (
        PREPARED_NAME,
        PROTOCOLS_NAME,
        SOURCE_MANIFEST_NAME,
        PREAUTHORIZATION_NAME,
        AUTHORIZATION_NAME,
        CLAIM_NAME,
        ACCESS_RECEIPT_NAME,
        QWEN_PREDICTIONS_NAME,
        PHOBERT_PREDICTIONS_NAME,
        RESULTS_NAME,
        REPORT_NAME,
        TERMINAL_NAME,
    )
    hashes = _artifact_hashes(root, artifact_names)
    manifest_payload = _canonical_json_bytes(
        {
            "schema_version": "phase41-evidence-manifest-v1",
            "status": "completed",
            "artifacts": [
                {"name": name, "sha256": digest} for name, digest in hashes
            ],
            "terminal_policy": {
                "rerun_permitted": False,
                "test_outcome_used_for_tuning": False,
                "unbiased_test_score_claim_after_deployment_fit": False,
            },
        }
    )
    _exclusive_write(root / EVIDENCE_MANIFEST_NAME, manifest_payload)
    return _manifest_from_disk(root)


def verify_phase41_evidence(output_root: Path) -> Phase41EvidenceManifest:
    """Verify already-frozen evidence without any predictor, opener, or split argument."""

    root = Path(output_root)
    verify_only(root)
    manifest = _manifest_from_disk(root)
    expected = _artifact_hashes(root, tuple(name for name, _ in manifest.artifacts))
    if expected != manifest.artifacts:
        raise ContractError("evidence manifest artifact hashes drifted")
    disposition_path = root / DEPLOYMENT_DISPOSITION_NAME
    if disposition_path.exists():
        disposition, _ = _load_canonical_json(
            disposition_path, "Phase 41 deployment-fit disposition"
        )
        if set(disposition) != {
            "schema_version",
            "choice",
            "evidence_manifest_sha256",
            "selected_checkpoint_identities",
            "unbiased_test_score_claim",
            "test_outcome_used_for_tuning",
        }:
            raise ContractError("deployment-fit disposition fields drifted")
        if (
            disposition["schema_version"] != "phase41-deployment-fit-disposition-v1"
            or disposition["evidence_manifest_sha256"]
            != manifest.evidence_manifest_sha256
            or disposition["unbiased_test_score_claim"] is not False
            or disposition["test_outcome_used_for_tuning"] is not False
        ):
            raise ContractError("deployment-fit disposition authority drifted")
        DeploymentFitDisposition(
            choice=disposition["choice"],  # type: ignore[arg-type]
            selected_checkpoint_identities=tuple(
                disposition["selected_checkpoint_identities"]  # type: ignore[arg-type]
            ),
        )
    return manifest


def freeze_deployment_fit_disposition(
    output_root: Path, disposition: DeploymentFitDisposition
) -> Path:
    root = Path(output_root)
    manifest = verify_phase41_evidence(root)
    request, _ = _load_canonical_json(root / PREPARED_NAME, "Phase 41 request")
    models = _parse_models(request["models"])
    expected = tuple(model.selected_checkpoint_identity for model in models)
    if disposition.selected_checkpoint_identities != expected:
        raise ContractError("deployment-fit checkpoint choice differs from precommitment")
    payload = _canonical_json_bytes(
        {
            "schema_version": "phase41-deployment-fit-disposition-v1",
            "choice": disposition.choice,
            "evidence_manifest_sha256": manifest.evidence_manifest_sha256,
            "selected_checkpoint_identities": list(
                disposition.selected_checkpoint_identities
            ),
            "unbiased_test_score_claim": False,
            "test_outcome_used_for_tuning": False,
        }
    )
    return _exclusive_write(root / DEPLOYMENT_DISPOSITION_NAME, payload)


def selected_phase41_checkpoint_identities(output_root: Path) -> tuple[str, str]:
    verify_phase41_preauthorization(output_root)
    request, _ = _load_canonical_json(
        Path(output_root) / PREPARED_NAME, "Phase 41 request"
    )
    models = _parse_models(request["models"])
    return tuple(model.selected_checkpoint_identity for model in models)


def prepare_phase41_from_canonical_authorities(
    output_root: Path,
) -> PreparedPhase41Evaluation:
    """Fail closed until Phase 40 freezes its final code-fixed preparation bundle.

    The synthetic production path is exercised through
    :func:`prepare_phase41_evaluation`.  This no-argument operator entry point
    deliberately refuses to guess at incomplete Phase 40 identities while the
    two training runs are still in flight.
    """

    del output_root
    raise ContractError(
        "canonical Phase 40 comparison/review closure is not yet frozen; "
        "Phase 41 preparation remains unavailable"
    )


__all__ = [
    "AlreadySpentError",
    "AuthorizationError",
    "ContractError",
    "DeploymentFitDisposition",
    "EXPLICIT_AUTHORIZATION_STATEMENT",
    "FrozenModelIdentity",
    "InMemorySnapshot",
    "LABEL_ORDER",
    "ModelIdentity",
    "OpaqueHeldOutAuthority",
    "PREDICTION_COLUMNS",
    "Phase41EvidenceManifest",
    "Prediction",
    "PreparedPhase41Evaluation",
    "_phase41_test_runtime",
    "authorize_phase41_evaluation",
    "authorize_evaluation",
    "comparison_statements",
    "compute_metrics",
    "freeze_deployment_fit_disposition",
    "prepare_phase41_evaluation",
    "prepare_phase41_from_canonical_authorities",
    "prepare_evaluation",
    "run_phase41_once",
    "run_once",
    "selected_phase41_checkpoint_identities",
    "verify_phase41_evidence",
    "verify_phase41_preauthorization",
    "verify_only",
]
