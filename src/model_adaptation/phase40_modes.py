"""Typed experiment and adaptation-mode contracts for Phase 40."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
import importlib
from typing import Any


APPROVED_BITSANDBYTES_VERSION = "0.50.1"
_PRELOAD_PROOF_SEAL = object()


class ModelFamily(StrEnum):
    """Model families admitted to the Phase 40 comparison."""

    QWEN = "qwen"
    PHOBERT = "phobert"


class AdaptationMode(StrEnum):
    """Positive adaptation modes; mode is never inferred from a missing flag."""

    LORA = "lora"
    QLORA = "qlora"
    CLASSIFICATION_HEAD = "classification-head"


class RunKind(StrEnum):
    """Bounded local probes and full evidence-producing runs."""

    PROBE = "probe"
    FULL = "full"


class ResolvedQwenMode(StrEnum):
    """Mode names written only after the corresponding proof completes."""

    FULL_PRECISION_LORA = "full-precision-lora"
    FOUR_BIT_QLORA = "4bit-qlora"


@dataclass(frozen=True, slots=True)
class QwenPreloadCapabilities:
    """Side-effect-free capabilities inspected before a model is loaded."""

    cuda_available: bool
    bitsandbytes_imported: bool
    bitsandbytes_version: str | None
    bitsandbytes_config_available: bool
    linear4bit_type: type[Any] | None
    kbit_preparation_available: bool


@dataclass(frozen=True, slots=True)
class QwenPreloadProof:
    """Validated Stage-1 result. It deliberately does not claim a resolved mode."""

    requested_mode: AdaptationMode
    cuda_available: bool
    bitsandbytes_version: str | None
    bitsandbytes_config_available: bool
    linear4bit_type: type[Any] | None
    kbit_preparation_available: bool
    _seal: object = field(default=None, repr=False, compare=False)

    def __post_init__(self) -> None:
        requested = AdaptationMode(self.requested_mode)
        object.__setattr__(self, "requested_mode", requested)
        if requested == AdaptationMode.CLASSIFICATION_HEAD:
            raise ValueError("Qwen preload proof cannot use classification-head mode")
        if self._seal is not _PRELOAD_PROOF_SEAL:
            raise ValueError("Qwen preload proof must be issued by prove_qwen_preload")
        if requested == AdaptationMode.QLORA and not (
            self.cuda_available
            and self.bitsandbytes_version == APPROVED_BITSANDBYTES_VERSION
            and self.bitsandbytes_config_available
            and isinstance(self.linear4bit_type, type)
            and self.kbit_preparation_available
        ):
            raise ValueError("incomplete QLoRA preload proof")


@dataclass(frozen=True, slots=True)
class AdapterGradientCheck:
    """One adapter parameter's post-backward gradient evidence."""

    parameter_name: str
    is_finite: bool
    is_nonzero: bool

    def __post_init__(self) -> None:
        if not isinstance(self.parameter_name, str) or not self.parameter_name:
            raise ValueError("adapter gradient parameter_name must be non-empty")
        if not isinstance(self.is_finite, bool) or not isinstance(self.is_nonzero, bool):
            raise ValueError("adapter gradient flags must be booleans")
        if self.is_nonzero and not self.is_finite:
            raise ValueError("a non-zero adapter gradient must also be finite")


@dataclass(frozen=True, slots=True)
class QuantizationProof:
    """Complete Stage-2 proof retained with a Qwen training result."""

    requested_mode: AdaptationMode
    resolved_mode: ResolvedQwenMode
    bitsandbytes_version: str | None
    load_in_4bit: bool
    nf4: bool
    double_quantization: bool
    is_loaded_in_4bit: bool
    linear4bit_modules: int
    kbit_preparation_applied: bool
    base_weights_frozen: bool
    adapter_only_trainables: bool
    adapter_trainable_count: int
    backward_with_adapter_gradients: bool
    adapter_gradient_finite_count: int
    adapter_gradient_nonzero_count: int

    def __post_init__(self) -> None:
        requested = AdaptationMode(self.requested_mode)
        resolved = ResolvedQwenMode(self.resolved_mode)
        object.__setattr__(self, "requested_mode", requested)
        object.__setattr__(self, "resolved_mode", resolved)
        valid_pair = (
            requested == AdaptationMode.LORA
            and resolved == ResolvedQwenMode.FULL_PRECISION_LORA
        ) or (
            requested == AdaptationMode.QLORA
            and resolved == ResolvedQwenMode.FOUR_BIT_QLORA
        )
        if not valid_pair:
            raise ValueError(
                f"requested mode {requested.value} and resolved mode {resolved.value} are inadmissible"
            )
        if not self.base_weights_frozen or not self.adapter_only_trainables or self.adapter_trainable_count < 1:
            raise ValueError("quantization proof requires frozen base weights and adapter-only trainables")
        if requested == AdaptationMode.QLORA:
            complete = (
                self.bitsandbytes_version == APPROVED_BITSANDBYTES_VERSION
                and self.load_in_4bit
                and self.nf4
                and self.double_quantization
                and self.is_loaded_in_4bit
                and self.linear4bit_modules > 0
                and self.kbit_preparation_applied
                and self.backward_with_adapter_gradients
                and self.adapter_gradient_finite_count == self.adapter_trainable_count
                and self.adapter_gradient_nonzero_count > 0
                and self.adapter_gradient_nonzero_count <= self.adapter_gradient_finite_count
            )
            if not complete:
                raise ValueError("incomplete genuine QLoRA quantization proof")
        else:
            non_quantized = (
                self.bitsandbytes_version is None
                and not self.load_in_4bit
                and not self.nf4
                and not self.double_quantization
                and not self.is_loaded_in_4bit
                and self.linear4bit_modules == 0
                and not self.kbit_preparation_applied
                and not self.backward_with_adapter_gradients
                and self.adapter_gradient_finite_count == 0
                and self.adapter_gradient_nonzero_count == 0
            )
            if not non_quantized:
                raise ValueError("ordinary LoRA proof must be symmetrically non-quantized")


_SUPPORTED_EXPERIMENTS = frozenset(
    {
        (ModelFamily.QWEN, AdaptationMode.LORA, RunKind.PROBE),
        (ModelFamily.QWEN, AdaptationMode.LORA, RunKind.FULL),
        (ModelFamily.QWEN, AdaptationMode.QLORA, RunKind.PROBE),
        (ModelFamily.QWEN, AdaptationMode.QLORA, RunKind.FULL),
        (ModelFamily.PHOBERT, AdaptationMode.CLASSIFICATION_HEAD, RunKind.FULL),
    }
)


@dataclass(frozen=True, slots=True)
class ExperimentIdentity:
    """One admissible ``(family, adaptation, run-kind)`` experiment tuple."""

    model_family: ModelFamily
    adaptation_mode: AdaptationMode
    run_kind: RunKind

    def __post_init__(self) -> None:
        try:
            family = ModelFamily(self.model_family)
            mode = AdaptationMode(self.adaptation_mode)
            kind = RunKind(self.run_kind)
        except ValueError as exc:
            raise ValueError(f"unsupported Phase 40 experiment identity: {exc}") from exc
        object.__setattr__(self, "model_family", family)
        object.__setattr__(self, "adaptation_mode", mode)
        object.__setattr__(self, "run_kind", kind)
        if (family, mode, kind) not in _SUPPORTED_EXPERIMENTS:
            raise ValueError(
                "unsupported Phase 40 experiment identity: "
                f"({family.value}, {mode.value}, {kind.value})"
            )

    def as_tuple(self) -> tuple[str, str, str]:
        """Return the stable serialized identity."""

        return (
            self.model_family.value,
            self.adaptation_mode.value,
            self.run_kind.value,
        )


def _has_bitsandbytes_linear4bit_identity(linear4bit_type: object) -> bool:
    return (
        isinstance(linear4bit_type, type)
        and linear4bit_type.__name__ == "Linear4bit"
        and linear4bit_type.__module__.startswith("bitsandbytes.")
    )


def _imported_bitsandbytes_linear4bit() -> tuple[object, type[Any] | None]:
    """Return the runtime module and its exact exported Linear4bit type."""

    try:
        bitsandbytes_module = importlib.import_module("bitsandbytes")
    except ImportError as exc:
        raise RuntimeError("QLoRA requires an importable bitsandbytes runtime") from exc
    linear4bit_type = getattr(
        getattr(bitsandbytes_module, "nn", None),
        "Linear4bit",
        None,
    )
    return bitsandbytes_module, linear4bit_type


def prove_qwen_preload(
    identity: ExperimentIdentity,
    capabilities: QwenPreloadCapabilities,
) -> QwenPreloadProof:
    """Validate Stage 1 before any Qwen model load or output creation."""

    if identity.model_family != ModelFamily.QWEN:
        raise ValueError("Qwen preload proof requires a qwen experiment identity")
    mode = identity.adaptation_mode
    if mode == AdaptationMode.CLASSIFICATION_HEAD:
        raise ValueError("Qwen does not support the classification-head adaptation mode")
    if mode == AdaptationMode.QLORA:
        if not capabilities.cuda_available:
            raise RuntimeError("QLoRA requires CUDA before model loading")
        if not capabilities.bitsandbytes_imported:
            raise RuntimeError("QLoRA requires an importable bitsandbytes runtime")
        bitsandbytes_module, runtime_linear4bit_type = _imported_bitsandbytes_linear4bit()
        runtime_version = str(getattr(bitsandbytes_module, "__version__", ""))
        if capabilities.bitsandbytes_version != APPROVED_BITSANDBYTES_VERSION:
            raise RuntimeError(
                "QLoRA requires the approved bitsandbytes version "
                f"{APPROVED_BITSANDBYTES_VERSION}; got {capabilities.bitsandbytes_version!r}"
            )
        if capabilities.bitsandbytes_version != runtime_version:
            raise RuntimeError(
                "QLoRA preload capabilities do not match the imported bitsandbytes runtime"
            )
        if not capabilities.bitsandbytes_config_available:
            raise RuntimeError("QLoRA requires Transformers BitsAndBytesConfig")
        if (
            capabilities.linear4bit_type is not runtime_linear4bit_type
            or not _has_bitsandbytes_linear4bit_identity(runtime_linear4bit_type)
        ):
            raise RuntimeError(
                "QLoRA requires the exact imported bitsandbytes.nn.Linear4bit type"
            )
        if not capabilities.kbit_preparation_available:
            raise RuntimeError("QLoRA requires prepare_model_for_kbit_training")
    return QwenPreloadProof(
        requested_mode=mode,
        cuda_available=capabilities.cuda_available,
        bitsandbytes_version=capabilities.bitsandbytes_version,
        bitsandbytes_config_available=capabilities.bitsandbytes_config_available,
        linear4bit_type=capabilities.linear4bit_type,
        kbit_preparation_available=capabilities.kbit_preparation_available,
        _seal=_PRELOAD_PROOF_SEAL,
    )


def _configuration_value(configuration: object | None, name: str, default: object = None) -> object:
    if configuration is None:
        return default
    if isinstance(configuration, dict):
        return configuration.get(name, default)
    return getattr(configuration, name, default)


def _is_linear4bit(module: object, linear4bit_type: type[Any] | None) -> bool:
    return linear4bit_type is not None and isinstance(module, linear4bit_type)


def _looks_like_bitsandbytes_linear4bit(module: object) -> bool:
    return _has_bitsandbytes_linear4bit_identity(type(module))


def prove_qwen_mode(
    identity: ExperimentIdentity,
    *,
    preload_proof: QwenPreloadProof,
    model: Any,
    quantization_config: object | None,
    kbit_preparation_applied: bool,
    backward_performed: bool,
    adapter_gradients: tuple[AdapterGradientCheck, ...],
) -> QuantizationProof:
    """Validate the loaded adapter and resolve LoRA or genuine QLoRA."""

    if identity.model_family != ModelFamily.QWEN:
        raise ValueError("Qwen mode proof requires a qwen experiment identity")
    if preload_proof.requested_mode != identity.adaptation_mode:
        raise RuntimeError("preload proof requested mode does not match the experiment identity")

    modules = tuple(model.modules())
    if identity.adaptation_mode == AdaptationMode.QLORA:
        linear4bit_modules = sum(
            _is_linear4bit(module, preload_proof.linear4bit_type) for module in modules
        )
    else:
        linear4bit_modules = sum(
            _looks_like_bitsandbytes_linear4bit(module) for module in modules
        )
    named_parameters = tuple(model.named_parameters())
    trainable_names = tuple(name for name, parameter in named_parameters if parameter.requires_grad)
    adapter_trainables = tuple(name for name in trainable_names if "lora_" in name.casefold())
    non_adapter_trainables = tuple(name for name in trainable_names if "lora_" not in name.casefold())
    base_weights_frozen = not non_adapter_trainables
    adapter_only = bool(adapter_trainables) and not non_adapter_trainables
    loaded_in_4bit = bool(getattr(model, "is_loaded_in_4bit", False))
    load_in_4bit = bool(_configuration_value(quantization_config, "load_in_4bit", False))
    nf4 = _configuration_value(quantization_config, "bnb_4bit_quant_type") == "nf4"
    double_quant = bool(
        _configuration_value(quantization_config, "bnb_4bit_use_double_quant", False)
    )

    if non_adapter_trainables:
        if any("base" in name.casefold() for name in non_adapter_trainables):
            raise RuntimeError(f"base weights are not frozen: {list(non_adapter_trainables[:5])}")
        raise RuntimeError(
            f"adapter-only trainables proof failed: {list(non_adapter_trainables[:5])}"
        )
    if not adapter_trainables:
        raise RuntimeError("no adapter trainable parameters were found")

    if identity.adaptation_mode == AdaptationMode.LORA:
        if quantization_config is not None or loaded_in_4bit or linear4bit_modules:
            raise RuntimeError("LoRA proof found a quantization config or Linear4bit base module")
        if kbit_preparation_applied or backward_performed or adapter_gradients:
            raise RuntimeError("LoRA proof must not claim QLoRA k-bit or gradient-proof steps")
        return QuantizationProof(
            requested_mode=AdaptationMode.LORA,
            resolved_mode=ResolvedQwenMode.FULL_PRECISION_LORA,
            bitsandbytes_version=None,
            load_in_4bit=False,
            nf4=False,
            double_quantization=False,
            is_loaded_in_4bit=False,
            linear4bit_modules=0,
            kbit_preparation_applied=False,
            base_weights_frozen=base_weights_frozen,
            adapter_only_trainables=adapter_only,
            adapter_trainable_count=len(adapter_trainables),
            backward_with_adapter_gradients=False,
            adapter_gradient_finite_count=0,
            adapter_gradient_nonzero_count=0,
        )

    if not load_in_4bit:
        raise RuntimeError("QLoRA quantization config must set load_in_4bit=True")
    if not nf4:
        raise RuntimeError("QLoRA quantization config must use NF4")
    if not double_quant:
        raise RuntimeError("QLoRA quantization config must enable double quantization")
    if not loaded_in_4bit:
        raise RuntimeError("QLoRA model must report is_loaded_in_4bit=True")
    if linear4bit_modules < 1:
        raise RuntimeError("QLoRA model must contain at least one Linear4bit module")
    if not kbit_preparation_applied:
        raise RuntimeError("QLoRA k-bit preparation was not applied")
    if not backward_performed:
        raise RuntimeError("QLoRA proof requires a real backward micro-batch")
    if not adapter_gradients:
        raise RuntimeError("QLoRA proof requires adapter gradient evidence")
    finite_count = sum(check.is_finite for check in adapter_gradients)
    nonzero_count = sum(check.is_nonzero for check in adapter_gradients)
    if finite_count != len(adapter_gradients):
        raise RuntimeError("QLoRA adapter gradients must all be finite")
    if nonzero_count < 1:
        raise RuntimeError("QLoRA requires at least one finite non-zero adapter gradient")
    gradient_names = {check.parameter_name for check in adapter_gradients}
    if gradient_names != set(adapter_trainables):
        raise RuntimeError("QLoRA gradient evidence must cover every trainable adapter parameter")

    return QuantizationProof(
        requested_mode=AdaptationMode.QLORA,
        resolved_mode=ResolvedQwenMode.FOUR_BIT_QLORA,
        bitsandbytes_version=preload_proof.bitsandbytes_version,
        load_in_4bit=load_in_4bit,
        nf4=nf4,
        double_quantization=double_quant,
        is_loaded_in_4bit=loaded_in_4bit,
        linear4bit_modules=linear4bit_modules,
        kbit_preparation_applied=kbit_preparation_applied,
        base_weights_frozen=base_weights_frozen,
        adapter_only_trainables=adapter_only,
        adapter_trainable_count=len(adapter_trainables),
        backward_with_adapter_gradients=True,
        adapter_gradient_finite_count=finite_count,
        adapter_gradient_nonzero_count=nonzero_count,
    )
