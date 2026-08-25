"""Frozen, model-specific inference contracts for Phase 41.

This module deliberately contains no transformers, torch, PEFT, filesystem-model
loader, or dataset import.  Phase 40 must construct and smoke-test the concrete
adapters before the irreversible evaluator is entered.  Phase 41 receives only
immutable protocol authorities and already-loaded callables.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import re
from typing import Callable, Mapping, Sequence, TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover - import cycle guard for type checkers
    from src.model_adaptation.phase41_evaluation import InMemorySnapshot, Prediction


SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
PROTOCOL_NAME = "frozen-inference-protocols.json"


class ProtocolContractError(RuntimeError):
    """A model identity or frozen inference protocol drifted."""


def _reject_duplicates(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ProtocolContractError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def canonical_json_bytes(value: object) -> bytes:
    return (
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
        + b"\n"
    )


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _require_sha(value: object, name: str) -> str:
    if not isinstance(value, str) or not SHA256_RE.fullmatch(value):
        raise ProtocolContractError(f"{name} must be a lowercase SHA-256")
    return value


@dataclass(frozen=True, slots=True)
class FrozenInferenceProtocol:
    """One complete immutable inference contract, excluding executable objects."""

    role: str
    body: Mapping[str, object]
    protocol_sha256: str

    def __post_init__(self) -> None:
        expected = "qwen" if self.role == "qwen" else "phobert" if self.role == "phobert" else None
        if expected is None:
            raise ProtocolContractError("protocol role must be qwen or phobert")
        if not isinstance(self.body, Mapping):
            raise ProtocolContractError("protocol body must be a mapping")
        canonical_body = dict(self.body)
        if canonical_body.get("role") != self.role:
            raise ProtocolContractError("protocol body role drifted")
        required = QWEN_FIELDS if self.role == "qwen" else PHOBERT_FIELDS
        if set(canonical_body) != required:
            raise ProtocolContractError(f"{self.role} protocol fields differ from the frozen contract")
        _validate_protocol_body(self.role, canonical_body)
        expected_sha = _sha256(canonical_json_bytes(canonical_body))
        if self.protocol_sha256 != expected_sha:
            raise ProtocolContractError(f"{self.role} protocol self-hash drifted")

    def as_dict(self) -> dict[str, object]:
        return {
            "role": self.role,
            "protocol_sha256": self.protocol_sha256,
            "body": dict(self.body),
        }


QWEN_FIELDS = {
    "role",
    "base_revision",
    "base_snapshot_sha256",
    "adapter_checkpoint_identity",
    "adapter_sha256",
    "tokenizer_sha256",
    "tokenizer_config_sha256",
    "prompt_template_utf8_sha256",
    "prompt_template_bytes",
    "decoder",
    "label_verbalizer",
    "parser_source_sha256",
    "invalid_output_mapping",
    "retry_policy",
    "runtime",
    "synthetic_smoke",
}

PHOBERT_FIELDS = {
    "role",
    "base_revision",
    "base_snapshot_sha256",
    "classifier_checkpoint_identity",
    "classifier_state_sha256",
    "tokenizer_sha256",
    "segmenter_sha256",
    "preprocessing",
    "max_length",
    "truncation",
    "padding",
    "label_index_map",
    "logit_shape",
    "decision_rule",
    "runtime",
    "synthetic_smoke",
}

_LABELS = (
    "bank_impersonation",
    "zalo_social_engineering",
    "task_scam",
    "benign",
)


def _validate_protocol_body(role: str, body: Mapping[str, object]) -> None:
    for key, value in body.items():
        if key.endswith("sha256"):
            _require_sha(value, f"{role}.{key}")
    if role == "qwen":
        if body["retry_policy"] != {"retries": 0, "repairs": False}:
            raise ProtocolContractError("Qwen retry/repair policy must stay disabled")
        if body["label_verbalizer"] != list(_LABELS):
            raise ProtocolContractError("Qwen label verbalizer drifted")
        if body["invalid_output_mapping"] != "invalid_output":
            raise ProtocolContractError("Qwen invalid-output mapping drifted")
        decoder = body["decoder"]
        if not isinstance(decoder, dict) or set(decoder) != {
            "do_sample",
            "temperature",
            "top_p",
            "max_new_tokens",
        }:
            raise ProtocolContractError("Qwen decoder controls are incomplete")
        if decoder["do_sample"] is not False or decoder["temperature"] != 0.0:
            raise ProtocolContractError("Qwen decoding must be deterministic")
    else:
        if body["label_index_map"] != {str(index): label for index, label in enumerate(_LABELS)}:
            raise ProtocolContractError("PhoBERT label-index map drifted")
        if body["logit_shape"] != [4] or body["decision_rule"] != "argmax":
            raise ProtocolContractError("PhoBERT four-logit argmax contract drifted")
        if not isinstance(body["max_length"], int) or body["max_length"] <= 0:
            raise ProtocolContractError("PhoBERT max_length must be positive")
    runtime = body["runtime"]
    if not isinstance(runtime, dict) or set(runtime) != {"python", "packages", "device"}:
        raise ProtocolContractError(f"{role} runtime identity is incomplete")
    smoke = body["synthetic_smoke"]
    if not isinstance(smoke, dict) or set(smoke) != {"input_sha256", "expected_state"}:
        raise ProtocolContractError(f"{role} synthetic smoke authority is incomplete")
    _require_sha(smoke["input_sha256"], f"{role}.synthetic_smoke.input_sha256")
    if smoke["expected_state"] not in _LABELS:
        raise ProtocolContractError(f"{role} synthetic smoke state is invalid")


@dataclass(frozen=True, slots=True)
class Phase41ProtocolAuthority:
    qwen: FrozenInferenceProtocol
    phobert: FrozenInferenceProtocol
    authority_sha256: str

    def __post_init__(self) -> None:
        if (self.qwen.role, self.phobert.role) != ("qwen", "phobert"):
            raise ProtocolContractError("protocol order must be Qwen then PhoBERT")
        expected = _sha256(canonical_json_bytes(self._body_without_hash()))
        if self.authority_sha256 != expected:
            raise ProtocolContractError("protocol authority self-hash drifted")

    def _body_without_hash(self) -> dict[str, object]:
        return {
            "schema_version": "phase41-frozen-inference-protocols-v1",
            "models": [self.qwen.as_dict(), self.phobert.as_dict()],
        }

    def as_dict(self) -> dict[str, object]:
        body = self._body_without_hash()
        body["authority_sha256"] = self.authority_sha256
        return body


PredictorCallable = Callable[["InMemorySnapshot"], Sequence["Prediction"]]


@dataclass(frozen=True, slots=True)
class FrozenQwenPredictor:
    protocol: FrozenInferenceProtocol
    predictor: PredictorCallable

    def __post_init__(self) -> None:
        if self.protocol.role != "qwen" or not callable(self.predictor):
            raise ProtocolContractError("Qwen predictor must be callable and protocol-bound")

    def __call__(self, snapshot: "InMemorySnapshot") -> Sequence["Prediction"]:
        return self.predictor(snapshot)


@dataclass(frozen=True, slots=True)
class FrozenPhoBertPredictor:
    protocol: FrozenInferenceProtocol
    predictor: PredictorCallable

    def __post_init__(self) -> None:
        if self.protocol.role != "phobert" or not callable(self.predictor):
            raise ProtocolContractError("PhoBERT predictor must be callable and protocol-bound")

    def __call__(self, snapshot: "InMemorySnapshot") -> Sequence["Prediction"]:
        return self.predictor(snapshot)


def _protocol(role: str, body: dict[str, object]) -> FrozenInferenceProtocol:
    return FrozenInferenceProtocol(role, body, _sha256(canonical_json_bytes(body)))


def build_synthetic_protocol_authority(models) -> Phase41ProtocolAuthority:  # noqa: ANN001
    """Build a complete fake authority for tests; it never loads a model."""

    qwen_model, phobert_model = tuple(models)
    smoke_sha = _sha256("tin nhắn tổng hợp".encode("utf-8"))
    runtime = {"python": "synthetic", "packages": {"fake": "1"}, "device": "cpu-fake"}
    qwen_body: dict[str, object] = {
        "role": "qwen",
        "base_revision": "synthetic-qwen-revision",
        "base_snapshot_sha256": "a" * 64,
        "adapter_checkpoint_identity": qwen_model.selected_checkpoint_identity,
        "adapter_sha256": qwen_model.artifact_sha256,
        "tokenizer_sha256": "b" * 64,
        "tokenizer_config_sha256": "c" * 64,
        "prompt_template_utf8_sha256": "d" * 64,
        "prompt_template_bytes": 128,
        "decoder": {"do_sample": False, "temperature": 0.0, "top_p": 1.0, "max_new_tokens": 16},
        "label_verbalizer": list(_LABELS),
        "parser_source_sha256": "e" * 64,
        "invalid_output_mapping": "invalid_output",
        "retry_policy": {"retries": 0, "repairs": False},
        "runtime": runtime,
        "synthetic_smoke": {"input_sha256": smoke_sha, "expected_state": "benign"},
    }
    phobert_body: dict[str, object] = {
        "role": "phobert",
        "base_revision": "synthetic-phobert-revision",
        "base_snapshot_sha256": "f" * 64,
        "classifier_checkpoint_identity": phobert_model.selected_checkpoint_identity,
        "classifier_state_sha256": phobert_model.artifact_sha256,
        "tokenizer_sha256": "0" * 64,
        "segmenter_sha256": "1" * 64,
        "preprocessing": ["unicode_nfc", "rdrsegmenter", "tokenizer"],
        "max_length": 256,
        "truncation": True,
        "padding": "max_length",
        "label_index_map": {str(index): label for index, label in enumerate(_LABELS)},
        "logit_shape": [4],
        "decision_rule": "argmax",
        "runtime": runtime,
        "synthetic_smoke": {"input_sha256": smoke_sha, "expected_state": "benign"},
    }
    qwen = _protocol("qwen", qwen_body)
    phobert = _protocol("phobert", phobert_body)
    body = {
        "schema_version": "phase41-frozen-inference-protocols-v1",
        "models": [qwen.as_dict(), phobert.as_dict()],
    }
    return Phase41ProtocolAuthority(qwen, phobert, _sha256(canonical_json_bytes(body)))


def write_protocol_authority(output_root: Path, authority: Phase41ProtocolAuthority) -> Path:
    root = Path(output_root)
    root.mkdir(parents=True, exist_ok=True)
    path = root / PROTOCOL_NAME
    payload = canonical_json_bytes(authority.as_dict())
    with path.open("xb") as handle:
        handle.write(payload)
        handle.flush()
    return path


def load_protocol_authority(output_root: Path) -> Phase41ProtocolAuthority:
    path = Path(output_root) / PROTOCOL_NAME
    payload = path.read_bytes()
    try:
        raw = json.loads(payload.decode("utf-8", errors="strict"), object_pairs_hook=_reject_duplicates)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ProtocolContractError("protocol authority is not strict JSON") from exc
    if not isinstance(raw, dict) or set(raw) != {"schema_version", "models", "authority_sha256"}:
        raise ProtocolContractError("protocol authority fields drifted")
    if raw["schema_version"] != "phase41-frozen-inference-protocols-v1" or payload != canonical_json_bytes(raw):
        raise ProtocolContractError("protocol authority schema/canonical bytes drifted")
    models = raw["models"]
    if not isinstance(models, list) or len(models) != 2:
        raise ProtocolContractError("protocol authority must contain two models")
    frozen: list[FrozenInferenceProtocol] = []
    for expected_role, item in zip(("qwen", "phobert"), models, strict=True):
        if not isinstance(item, dict) or set(item) != {"role", "protocol_sha256", "body"}:
            raise ProtocolContractError("protocol model record fields drifted")
        if item["role"] != expected_role or not isinstance(item["body"], dict):
            raise ProtocolContractError("protocol model order/body drifted")
        frozen.append(FrozenInferenceProtocol(expected_role, item["body"], item["protocol_sha256"]))
    return Phase41ProtocolAuthority(frozen[0], frozen[1], raw["authority_sha256"])


def load_phase41_production_predictors(
    output_root: Path,
) -> tuple[FrozenQwenPredictor, FrozenPhoBertPredictor]:
    """Fail closed until Phase 40 supplies the selected model loader receipts.

    Keeping this loader lazy prevents verify-only commands from importing GPU
    libraries.  Phase 41-02 may call it only after Phase 40's terminal model
    evidence and human authorization exist.
    """

    load_protocol_authority(output_root)
    raise ProtocolContractError(
        "Phase 40 selected model loader receipts are not frozen; run-once is unavailable"
    )


__all__ = [
    "FrozenInferenceProtocol",
    "FrozenPhoBertPredictor",
    "FrozenQwenPredictor",
    "PROTOCOL_NAME",
    "Phase41ProtocolAuthority",
    "ProtocolContractError",
    "build_synthetic_protocol_authority",
    "canonical_json_bytes",
    "load_protocol_authority",
    "load_phase41_production_predictors",
    "write_protocol_authority",
]
