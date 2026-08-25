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
from types import MappingProxyType
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
    value = _deep_thaw(value)
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


def _deep_freeze(value: object) -> object:
    if isinstance(value, Mapping):
        return MappingProxyType({key: _deep_freeze(item) for key, item in value.items()})
    if isinstance(value, (list, tuple)):
        return tuple(_deep_freeze(item) for item in value)
    return value


def _deep_thaw(value: object) -> object:
    if isinstance(value, Mapping):
        return {key: _deep_thaw(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_deep_thaw(item) for item in value]
    return value


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
        canonical_body = _deep_thaw(self.body)
        if not isinstance(canonical_body, dict):
            raise ProtocolContractError("protocol body must be a mapping")
        if canonical_body.get("role") != self.role:
            raise ProtocolContractError("protocol body role drifted")
        required = QWEN_FIELDS if self.role == "qwen" else PHOBERT_FIELDS
        if set(canonical_body) != required:
            raise ProtocolContractError(f"{self.role} protocol fields differ from the frozen contract")
        _validate_protocol_body(self.role, canonical_body)
        expected_sha = _sha256(canonical_json_bytes(canonical_body))
        if self.protocol_sha256 != expected_sha:
            raise ProtocolContractError(f"{self.role} protocol self-hash drifted")
        object.__setattr__(self, "body", _deep_freeze(canonical_body))

    def as_dict(self) -> dict[str, object]:
        return {
            "role": self.role,
            "protocol_sha256": self.protocol_sha256,
            "body": _deep_thaw(self.body),
        }


QWEN_FIELDS = {
    "role",
    "bundle_root",
    "base_model_id",
    "base_revision",
    "base_snapshot_sha256",
    "model_artifact_relative_path",
    "tokenizer_artifact_relative_path",
    "adapter_checkpoint_identity",
    "adapter_sha256",
    "tokenizer_sha256",
    "tokenizer_config_sha256",
    "prompt_template_utf8_sha256",
    "prompt_template_bytes",
    "prompt_template",
    "formatter_sha256",
    "max_sequence_length",
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
    "bundle_root",
    "base_model_id",
    "base_revision",
    "base_snapshot_sha256",
    "model_artifact_relative_path",
    "tokenizer_artifact_relative_path",
    "classifier_checkpoint_identity",
    "classifier_state_sha256",
    "tokenizer_sha256",
    "preprocessor_sha256",
    "segmenter_package",
    "segmenter_version",
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
        template = body["prompt_template"]
        if not isinstance(template, str) or template.count("{text}") != 1:
            raise ProtocolContractError("Qwen prompt template must contain one text slot")
        encoded_template = template.encode("utf-8", errors="strict")
        if body["prompt_template_bytes"] != len(encoded_template) or body[
            "prompt_template_utf8_sha256"
        ] != _sha256(encoded_template):
            raise ProtocolContractError("Qwen prompt template bytes/hash drifted")
        try:
            template_record = json.loads(
                template,
                object_pairs_hook=_reject_duplicates,
                parse_constant=lambda value: (_ for _ in ()).throw(
                    ProtocolContractError(
                        f"non-finite JSON constant is forbidden: {value}"
                    )
                ),
            )
        except (json.JSONDecodeError, ProtocolContractError) as exc:
            raise ProtocolContractError("Qwen prompt template is not strict JSON") from exc
        if (
            not isinstance(template_record, dict)
            or set(template_record) != {"system_instruction", "user_template"}
            or not isinstance(template_record["system_instruction"], str)
            or not template_record["system_instruction"]
            or not isinstance(template_record["user_template"], str)
            or template_record["user_template"].count("{text}") != 1
        ):
            raise ProtocolContractError("Qwen prompt template structure drifted")
        if (
            not isinstance(body["max_sequence_length"], int)
            or isinstance(body["max_sequence_length"], bool)
            or body["max_sequence_length"] <= 0
        ):
            raise ProtocolContractError("Qwen max sequence length must be positive")
        if body["retry_policy"] != {"retries": 0, "repairs": False}:
            raise ProtocolContractError("Qwen retry/repair policy must stay disabled")
        if body["label_verbalizer"] != list(_LABELS):
            raise ProtocolContractError("Qwen label verbalizer drifted")
        if body["invalid_output_mapping"] != "invalid_output":
            raise ProtocolContractError("Qwen invalid-output mapping drifted")
        decoder = body["decoder"]
        if not isinstance(decoder, dict) or set(decoder) != {
            "do_sample",
            "num_return_sequences",
            "temperature",
            "top_p",
            "max_new_tokens",
        }:
            raise ProtocolContractError("Qwen decoder controls are incomplete")
        if (
            decoder["do_sample"] is not False
            or decoder["num_return_sequences"] != 1
            or decoder["temperature"] != 0.0
        ):
            raise ProtocolContractError("Qwen decoding must be deterministic")
    else:
        if body["label_index_map"] != {str(index): label for index, label in enumerate(_LABELS)}:
            raise ProtocolContractError("PhoBERT label-index map drifted")
        if body["logit_shape"] != [4] or body["decision_rule"] != "argmax":
            raise ProtocolContractError("PhoBERT four-logit argmax contract drifted")
        if body["max_length"] != 256:
            raise ProtocolContractError("PhoBERT max_length must remain 256")
        if body["truncation"] != "right" or body["padding"] != "dynamic-longest":
            raise ProtocolContractError("PhoBERT truncation/padding policy drifted")
        if body["segmenter_package"] != "underthesea" or body["segmenter_version"] != "9.5.0":
            raise ProtocolContractError("PhoBERT segmenter identity drifted")
        if body["preprocessing"] != [
            "raw_text_utf8_strict_no_normalization",
            "underthesea.word_tokenize(format=text)",
            "tokenizer(add_special_tokens=true)",
        ]:
            raise ProtocolContractError("PhoBERT preprocessing sequence drifted")
    runtime = body["runtime"]
    if not isinstance(runtime, dict) or set(runtime) != {"python", "packages", "device"}:
        raise ProtocolContractError(f"{role} runtime identity is incomplete")
    packages = runtime["packages"]
    if not isinstance(packages, dict) or not packages:
        raise ProtocolContractError(f"{role} runtime package identity is incomplete")
    if role == "phobert" and packages.get("underthesea") != body["segmenter_version"]:
        raise ProtocolContractError("PhoBERT segmenter package/version drifted")
    smoke = body["synthetic_smoke"]
    if not isinstance(smoke, dict) or set(smoke) != {"input_sha256", "expected_state"}:
        raise ProtocolContractError(f"{role} synthetic smoke authority is incomplete")
    _require_sha(smoke["input_sha256"], f"{role}.synthetic_smoke.input_sha256")
    if smoke["expected_state"] not in _LABELS:
        raise ProtocolContractError(f"{role} synthetic smoke state is invalid")
    for key in ("bundle_root", "model_artifact_relative_path", "tokenizer_artifact_relative_path"):
        value = body[key]
        if not isinstance(value, str) or not value or Path(value).is_absolute() or ".." in Path(value).parts:
            raise ProtocolContractError(f"{role}.{key} must be a safe repository-relative path")
    if not isinstance(body["base_model_id"], str) or not body["base_model_id"]:
        raise ProtocolContractError(f"{role} base model id is missing")
    if not isinstance(body["base_revision"], str) or not body["base_revision"]:
        raise ProtocolContractError(f"{role} base revision is missing")


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
    loaded: bool = True
    smoke_verified: bool = True

    def __post_init__(self) -> None:
        if self.protocol.role != "qwen" or not callable(self.predictor):
            raise ProtocolContractError("Qwen predictor must be callable and protocol-bound")
        if self.loaded is not True or self.smoke_verified is not True:
            raise ProtocolContractError("Qwen predictor must be loaded and smoke-verified")

    def __call__(self, snapshot: "InMemorySnapshot") -> Sequence["Prediction"]:
        return self.predictor(snapshot)


@dataclass(frozen=True, slots=True)
class FrozenPhoBertPredictor:
    protocol: FrozenInferenceProtocol
    predictor: PredictorCallable
    loaded: bool = True
    smoke_verified: bool = True

    def __post_init__(self) -> None:
        if self.protocol.role != "phobert" or not callable(self.predictor):
            raise ProtocolContractError("PhoBERT predictor must be callable and protocol-bound")
        if self.loaded is not True or self.smoke_verified is not True:
            raise ProtocolContractError("PhoBERT predictor must be loaded and smoke-verified")

    def __call__(self, snapshot: "InMemorySnapshot") -> Sequence["Prediction"]:
        return self.predictor(snapshot)


def _protocol(role: str, body: dict[str, object]) -> FrozenInferenceProtocol:
    return FrozenInferenceProtocol(role, body, _sha256(canonical_json_bytes(body)))


def build_protocol_authority(
    qwen_body: Mapping[str, object], phobert_body: Mapping[str, object]
) -> Phase41ProtocolAuthority:
    qwen = _protocol("qwen", dict(qwen_body))
    phobert = _protocol("phobert", dict(phobert_body))
    body = {
        "schema_version": "phase41-frozen-inference-protocols-v1",
        "models": [qwen.as_dict(), phobert.as_dict()],
    }
    return Phase41ProtocolAuthority(
        qwen, phobert, _sha256(canonical_json_bytes(body))
    )


def build_synthetic_protocol_authority(models) -> Phase41ProtocolAuthority:  # noqa: ANN001
    """Build a complete fake authority for tests; it never loads a model."""

    qwen_model, phobert_model = tuple(models)
    smoke_sha = _sha256("tin nhắn tổng hợp".encode("utf-8"))
    qwen_runtime = {
        "python": "synthetic",
        "packages": {"fake": "1"},
        "device": "cpu-fake",
    }
    phobert_runtime = {
        "python": "synthetic",
        "packages": {"fake": "1", "underthesea": "9.5.0"},
        "device": "cpu-fake",
    }
    qwen_body: dict[str, object] = {
        "role": "qwen",
        "bundle_root": "synthetic/qwen",
        "base_model_id": "synthetic/qwen",
        "base_revision": "synthetic-qwen-revision",
        "base_snapshot_sha256": "a" * 64,
        "model_artifact_relative_path": "model-artifact",
        "tokenizer_artifact_relative_path": "tokenizer",
        "adapter_checkpoint_identity": qwen_model.selected_checkpoint_identity,
        "adapter_sha256": qwen_model.artifact_sha256,
        "tokenizer_sha256": "b" * 64,
        "tokenizer_config_sha256": "c" * 64,
        "prompt_template_utf8_sha256": "d" * 64,
        "prompt_template_bytes": 0,
        "prompt_template": json.dumps(
            {
                "system_instruction": "Classify one synthetic Vietnamese message.",
                "user_template": (
                    "<UNTRUSTED_RAW_MESSAGE_JSON>\n{text}\n"
                    "</UNTRUSTED_RAW_MESSAGE_JSON>"
                ),
            },
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ),
        "formatter_sha256": "9" * 64,
        "max_sequence_length": 512,
        "decoder": {
            "do_sample": False,
            "num_return_sequences": 1,
            "temperature": 0.0,
            "top_p": 1.0,
            "max_new_tokens": 16,
        },
        "label_verbalizer": list(_LABELS),
        "parser_source_sha256": "e" * 64,
        "invalid_output_mapping": "invalid_output",
        "retry_policy": {"retries": 0, "repairs": False},
        "runtime": qwen_runtime,
        "synthetic_smoke": {"input_sha256": smoke_sha, "expected_state": "benign"},
    }
    phobert_body: dict[str, object] = {
        "role": "phobert",
        "bundle_root": "synthetic/phobert",
        "base_model_id": "synthetic/phobert",
        "base_revision": "synthetic-phobert-revision",
        "base_snapshot_sha256": "f" * 64,
        "model_artifact_relative_path": "model-artifact",
        "tokenizer_artifact_relative_path": "tokenizer",
        "classifier_checkpoint_identity": phobert_model.selected_checkpoint_identity,
        "classifier_state_sha256": phobert_model.artifact_sha256,
        "tokenizer_sha256": "0" * 64,
        "preprocessor_sha256": "1" * 64,
        "segmenter_package": "underthesea",
        "segmenter_version": "9.5.0",
        "preprocessing": [
            "raw_text_utf8_strict_no_normalization",
            "underthesea.word_tokenize(format=text)",
            "tokenizer(add_special_tokens=true)",
        ],
        "max_length": 256,
        "truncation": "right",
        "padding": "dynamic-longest",
        "label_index_map": {str(index): label for index, label in enumerate(_LABELS)},
        "logit_shape": [4],
        "decision_rule": "argmax",
        "runtime": phobert_runtime,
        "synthetic_smoke": {"input_sha256": smoke_sha, "expected_state": "benign"},
    }
    prompt_bytes = qwen_body["prompt_template"].encode("utf-8")  # type: ignore[union-attr]
    qwen_body["prompt_template_bytes"] = len(prompt_bytes)
    qwen_body["prompt_template_utf8_sha256"] = _sha256(prompt_bytes)
    return build_protocol_authority(qwen_body, phobert_body)


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
        raw = json.loads(
            payload.decode("utf-8", errors="strict"),
            object_pairs_hook=_reject_duplicates,
            parse_constant=lambda value: (_ for _ in ()).throw(
                ProtocolContractError(f"non-finite JSON constant is forbidden: {value}")
            ),
        )
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
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
    """Load and smoke the two code-fixed local artifacts without a data opener.

    Heavy libraries are imported only inside this run-only function, so prepare
    and verify-only commands cannot allocate GPU memory or load a model.
    """

    import importlib.metadata

    from src.model_adaptation.registry import build_model_checksum

    authority = load_protocol_authority(output_root)
    repository_root = Path(__file__).resolve().parents[2]

    def artifact(protocol: FrozenInferenceProtocol, key: str, expected_sha: str) -> Path:
        bundle = repository_root / str(protocol.body["bundle_root"])
        relative = Path(str(protocol.body[key]))
        target = bundle / relative
        if not target.exists() or target.is_symlink():
            raise ProtocolContractError(f"{protocol.role} bound artifact is absent: {key}")
        if build_model_checksum(target) != expected_sha:
            raise ProtocolContractError(f"{protocol.role} bound artifact hash drifted: {key}")
        return target

    def verify_packages(protocol: FrozenInferenceProtocol) -> None:
        runtime = protocol.body["runtime"]
        assert isinstance(runtime, Mapping)
        packages = runtime["packages"]
        if not isinstance(packages, Mapping) or not packages:
            raise ProtocolContractError(f"{protocol.role} runtime packages are missing")
        for package, expected in packages.items():
            try:
                observed = importlib.metadata.version(str(package))
            except importlib.metadata.PackageNotFoundError as exc:
                raise ProtocolContractError(
                    f"{protocol.role} runtime package is unavailable: {package}"
                ) from exc
            if observed != expected:
                raise ProtocolContractError(
                    f"{protocol.role} runtime package drifted: {package}"
                )

    verify_packages(authority.qwen)
    verify_packages(authority.phobert)
    qwen_model_root = artifact(
        authority.qwen,
        "model_artifact_relative_path",
        str(authority.qwen.body["adapter_sha256"]),
    )
    qwen_tokenizer_root = artifact(
        authority.qwen,
        "tokenizer_artifact_relative_path",
        str(authority.qwen.body["tokenizer_sha256"]),
    )
    phobert_model_root = artifact(
        authority.phobert,
        "model_artifact_relative_path",
        str(authority.phobert.body["classifier_state_sha256"]),
    )
    phobert_tokenizer_root = artifact(
        authority.phobert,
        "tokenizer_artifact_relative_path",
        str(authority.phobert.body["tokenizer_sha256"]),
    )

    try:
        import torch
        from huggingface_hub import snapshot_download
        import src.model_adaptation.phase40_metrics as phase40_metrics
        from src.model_adaptation.phase40_metrics import parse_qwen_prediction
        from src.model_adaptation.phobert_training import (
            PHOBERT_BASE_MODEL_MANIFEST_NAME,
            PHOBERT_PREPROCESSOR_SHA256,
            verify_phobert_base_model_provenance,
        )
        from src.model_adaptation.training import (
            PHASE40_BASE_MODEL_MANIFEST_NAME,
            _formatter_sha256,
            verify_qwen_base_model_provenance,
        )
        from transformers import (
            AutoModelForCausalLM,
            AutoModelForSequenceClassification,
            AutoTokenizer,
        )
        from peft import PeftModel
        from underthesea import word_tokenize
    except ImportError as exc:  # pragma: no cover - depends on run-only environment
        raise ProtocolContractError("Phase 41 model runtime dependencies are unavailable") from exc

    qwen_base_root = Path(
        snapshot_download(
            repo_id=str(authority.qwen.body["base_model_id"]),
            revision=str(authority.qwen.body["base_revision"]),
            local_files_only=True,
        )
    )
    qwen_base = verify_qwen_base_model_provenance(
        qwen_base_root,
        qwen_model_root / PHASE40_BASE_MODEL_MANIFEST_NAME,
        model_id=str(authority.qwen.body["base_model_id"]),
        model_revision=str(authority.qwen.body["base_revision"]),
    )
    if qwen_base.snapshot_content_sha256 != authority.qwen.body["base_snapshot_sha256"]:
        raise ProtocolContractError("Qwen base snapshot identity drifted")
    phobert_base_root = Path(
        snapshot_download(
            repo_id=str(authority.phobert.body["base_model_id"]),
            revision=str(authority.phobert.body["base_revision"]),
            local_files_only=True,
        )
    )
    phobert_base = verify_phobert_base_model_provenance(
        phobert_base_root,
        phobert_model_root / PHOBERT_BASE_MODEL_MANIFEST_NAME,
    )
    if (
        phobert_base.snapshot_content_sha256
        != authority.phobert.body["base_snapshot_sha256"]
        or authority.phobert.body["preprocessor_sha256"]
        != PHOBERT_PREPROCESSOR_SHA256
    ):
        raise ProtocolContractError("PhoBERT base/preprocessor identity drifted")

    qwen_tokenizer = AutoTokenizer.from_pretrained(
        qwen_tokenizer_root, local_files_only=True, trust_remote_code=False
    )
    tokenizer_config_path = qwen_tokenizer_root / "tokenizer_config.json"
    metrics_source_path = Path(str(phase40_metrics.__file__))
    if (
        not tokenizer_config_path.is_file()
        or tokenizer_config_path.is_symlink()
        or _sha256(tokenizer_config_path.read_bytes())
        != authority.qwen.body["tokenizer_config_sha256"]
        or not metrics_source_path.is_file()
        or metrics_source_path.is_symlink()
        or _sha256(metrics_source_path.read_bytes())
        != authority.qwen.body["parser_source_sha256"]
    ):
        raise ProtocolContractError("Qwen tokenizer/parser source identity drifted")
    prompt_template = json.loads(str(authority.qwen.body["prompt_template"]))
    formatter_sha256 = _formatter_sha256(
        qwen_tokenizer,
        system_instruction=str(prompt_template["system_instruction"]),
        max_length=int(authority.qwen.body["max_sequence_length"]),
    )
    if formatter_sha256 != authority.qwen.body["formatter_sha256"]:
        raise ProtocolContractError("Qwen tokenizer/chat formatter identity drifted")
    qwen_base = AutoModelForCausalLM.from_pretrained(
        qwen_base_root,
        local_files_only=True,
        trust_remote_code=False,
        device_map="auto",
    )
    qwen_model = PeftModel.from_pretrained(
        qwen_base, qwen_model_root, is_trainable=False
    )
    qwen_model.eval()

    phobert_tokenizer = AutoTokenizer.from_pretrained(
        phobert_tokenizer_root, local_files_only=True, trust_remote_code=False
    )
    phobert_model = AutoModelForSequenceClassification.from_pretrained(
        phobert_model_root,
        local_files_only=True,
        trust_remote_code=False,
    )
    phobert_device = torch.device(
        "cuda" if str(authority.phobert.body["runtime"]["device"]).startswith("cuda") else "cpu"
    )
    phobert_model.to(phobert_device)
    phobert_model.eval()

    from src.model_adaptation.phase41_evaluation import (
        InMemorySnapshot,
        InferenceRow,
        Prediction,
    )

    def qwen_predict(snapshot: InMemorySnapshot):  # noqa: ANN202
        predictions = []
        template = json.loads(str(authority.qwen.body["prompt_template"]))
        decoder = dict(authority.qwen.body["decoder"])
        for row in snapshot.rows:
            raw_message = json.dumps(
                {"raw_message": row.text},
                ensure_ascii=False,
                separators=(",", ":"),
            )
            user_content = str(template["user_template"]).replace("{text}", raw_message)
            messages = (
                {"role": "system", "content": str(template["system_instruction"])},
                {"role": "user", "content": user_content},
            )
            encoded = qwen_tokenizer.apply_chat_template(
                messages,
                tokenize=True,
                add_generation_prompt=True,
                return_tensors="pt",
                return_dict=True,
                enable_thinking=False,
            )
            if not isinstance(encoded, Mapping) or "input_ids" not in encoded:
                raise ProtocolContractError("Qwen chat template returned an invalid batch")
            target_device = next(qwen_model.parameters()).device
            encoded = {key: value.to(target_device) for key, value in encoded.items()}
            input_length = int(encoded["input_ids"].shape[-1])
            generation_controls = {
                "do_sample": decoder["do_sample"],
                "num_return_sequences": decoder["num_return_sequences"],
                "max_new_tokens": decoder["max_new_tokens"],
            }
            with torch.inference_mode():
                output = qwen_model.generate(**encoded, **generation_controls)
            raw = qwen_tokenizer.decode(output[0][input_length:], skip_special_tokens=True)
            parsed = parse_qwen_prediction(raw)
            state = parsed.state.value
            error = "invalid_qwen_output" if state == "invalid_output" else None
            predictions.append(Prediction(row.row_id, state, raw, error))
        return tuple(predictions)

    def phobert_predict(snapshot: InMemorySnapshot):  # noqa: ANN202
        index_map = authority.phobert.body["label_index_map"]
        assert isinstance(index_map, Mapping)
        if getattr(phobert_tokenizer, "truncation_side", "right") != "right":
            raise ProtocolContractError("PhoBERT tokenizer truncation side drifted")
        segmented = tuple(word_tokenize(row.text, format="text") for row in snapshot.rows)
        if any(not isinstance(value, str) or not value.strip() for value in segmented):
            raise ProtocolContractError("PhoBERT segmenter returned an invalid value")
        encoded = phobert_tokenizer(
            list(segmented),
            add_special_tokens=True,
            max_length=int(authority.phobert.body["max_length"]),
            truncation=True,
            padding="longest",
            return_tensors="pt",
        )
        encoded = {key: value.to(phobert_device) for key, value in encoded.items()}
        with torch.inference_mode():
            logits = phobert_model(**encoded).logits
        if tuple(logits.shape) != (len(snapshot.rows), 4) or not torch.isfinite(logits).all().item():
            raise ProtocolContractError("PhoBERT logits differ from the frozen four-logit contract")
        indices = torch.argmax(logits, dim=-1).tolist()
        return tuple(
            Prediction(row.row_id, str(index_map[str(index)]), str(index_map[str(index)]), None)
            for row, index in zip(snapshot.rows, indices, strict=True)
        )

    qwen = FrozenQwenPredictor(authority.qwen, qwen_predict)
    phobert = FrozenPhoBertPredictor(authority.phobert, phobert_predict)
    smoke_text = "tin nhắn tổng hợp"
    smoke = InMemorySnapshot((InferenceRow("phase41-smoke", 0, smoke_text),))
    for protocol, predictor in ((authority.qwen, qwen), (authority.phobert, phobert)):
        expected_hash = protocol.body["synthetic_smoke"]["input_sha256"]
        if _sha256(smoke_text.encode("utf-8")) != expected_hash:
            raise ProtocolContractError(f"{protocol.role} synthetic smoke input drifted")
        predictions = tuple(predictor(smoke))
        expected_state = protocol.body["synthetic_smoke"]["expected_state"]
        if len(predictions) != 1 or predictions[0].predicted_state != expected_state:
            raise ProtocolContractError(f"{protocol.role} synthetic smoke output drifted")
    return qwen, phobert


__all__ = [
    "FrozenInferenceProtocol",
    "FrozenPhoBertPredictor",
    "FrozenQwenPredictor",
    "PROTOCOL_NAME",
    "Phase41ProtocolAuthority",
    "ProtocolContractError",
    "build_synthetic_protocol_authority",
    "build_protocol_authority",
    "canonical_json_bytes",
    "load_protocol_authority",
    "load_phase41_production_predictors",
    "write_protocol_authority",
]
