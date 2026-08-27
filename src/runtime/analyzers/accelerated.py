"""Optional GPU-accelerated local analysis of Vietnamese phishing risk."""

from __future__ import annotations

import importlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from src.artifacts import (
    VerifiedArtifact,
    load_model_registry,
    resolve_downloaded_model,
    resolve_registry_artifact,
    verify_artifact_identity,
)
from src.config.settings import get_runtime_settings as get_settings
from src.runtime.analyzers.local_model import (
    build_analysis_result,
    build_structured_analysis_prompt,
    extract_structured_payload,
)
from src.runtime.contracts import AnalysisRequest, AnalysisResult, DoctorCheck, DoctorStatus


ACCELERATED_SETUP_GUIDE = (
    "Install local training extras with python -m pip install -e .[dev,train] and register the selected adapter and base-model artifacts."
)


@dataclass
class AcceleratedAnalyzer:
    """Contract-compatible accelerated backend backed by the selected runner-up artifact."""

    registry_path: Path = field(
        default_factory=lambda: get_settings().resolved_model_registry_path
    )
    artifact_root: Path = field(
        default_factory=lambda: get_settings().resolved_model_artifact_root
    )
    storage_root: Path = field(
        default_factory=lambda: get_settings().resolved_model_storage_root
    )
    runtime_profile: str = field(default_factory=lambda: get_settings().runtime_profile_accelerated)
    backend_name: str = "accelerated"
    _cached_runtime: Any | None = field(default=None, init=False, repr=False)
    _cached_adapter: VerifiedArtifact | None = field(default=None, init=False, repr=False)
    _cached_base_model: VerifiedArtifact | None = field(default=None, init=False, repr=False)

    def _resolve_runtime_paths(self) -> tuple[str, VerifiedArtifact, VerifiedArtifact]:
        registry = load_model_registry(self.registry_path, storage_root=self.storage_root)
        if registry.selection is None:
            raise RuntimeError("Pilot selection metadata is missing")

        target_candidate_id = registry.selection.runner_up_id
        adapter_artifact = resolve_registry_artifact(
            registry,
            artifact_root=self.artifact_root,
            candidate_id=target_candidate_id,
            artifact_type="adapter",
            profile_name=self.runtime_profile,
        )
        base_model = resolve_downloaded_model(self.artifact_root, target_candidate_id)
        return target_candidate_id, adapter_artifact, base_model

    def _load_runtime(
        self,
        *,
        adapter_artifact: VerifiedArtifact,
        base_model: VerifiedArtifact,
    ) -> Any:
        adapter_path = verify_artifact_identity(adapter_artifact)
        base_model_path = verify_artifact_identity(base_model)
        if (
            self._cached_runtime is not None
            and self._cached_adapter == adapter_artifact
            and self._cached_base_model == base_model
        ):
            return self._cached_runtime

        torch_module = importlib.import_module("torch")
        transformers_module = importlib.import_module("transformers")
        peft_module = importlib.import_module("peft")

        if not torch_module.cuda.is_available():
            raise RuntimeError("CUDA is required for the accelerated runtime profile")

        tokenizer = transformers_module.AutoTokenizer.from_pretrained(
            str(base_model_path),
            local_files_only=True,
            trust_remote_code=False,
        )
        if tokenizer.pad_token is None:
            tokenizer.pad_token = tokenizer.eos_token or tokenizer.unk_token

        model_load_kwargs: dict[str, Any] = {
            "local_files_only": True,
            "trust_remote_code": False,
            "use_safetensors": True,
            "low_cpu_mem_usage": True,
        }
        if importlib.util.find_spec("bitsandbytes") is not None and hasattr(transformers_module, "BitsAndBytesConfig"):
            compute_dtype = (
                torch_module.bfloat16 if torch_module.cuda.is_bf16_supported() else torch_module.float16
            )
            model_load_kwargs["quantization_config"] = transformers_module.BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_compute_dtype=compute_dtype,
                bnb_4bit_quant_type="nf4",
                bnb_4bit_use_double_quant=True,
            )
            model_load_kwargs["device_map"] = {"": 0}
        else:
            model_load_kwargs["device_map"] = {"": 0}
            model_load_kwargs["torch_dtype"] = (
                torch_module.bfloat16 if torch_module.cuda.is_bf16_supported() else torch_module.float16
            )

        model = transformers_module.AutoModelForCausalLM.from_pretrained(
            str(base_model_path),
            **model_load_kwargs,
        )
        model = peft_module.PeftModel.from_pretrained(
            model,
            str(adapter_path),
            is_trainable=False,
            local_files_only=True,
            use_safetensors=True,
        )
        if hasattr(model, "eval"):
            model.eval()

        self._cached_runtime = {
            "model": model,
            "tokenizer": tokenizer,
            "device": "cuda",
        }
        self._cached_adapter = adapter_artifact
        self._cached_base_model = base_model
        return self._cached_runtime

    def _infer_payload(self, runtime: Any, text: str) -> dict[str, Any]:
        tokenizer = runtime["tokenizer"]
        model = runtime["model"]
        prompt = build_structured_analysis_prompt(text)
        if hasattr(tokenizer, "apply_chat_template"):
            try:
                prompt = tokenizer.apply_chat_template(
                    [{"role": "user", "content": prompt}],
                    tokenize=False,
                    add_generation_prompt=True,
                    enable_thinking=False,
                )
            except Exception:
                pass

        encoded = tokenizer(prompt, return_tensors="pt")
        encoded = {key: value.to(runtime["device"]) for key, value in encoded.items()}
        output_ids = model.generate(
            **encoded,
            max_new_tokens=256,
            do_sample=False,
            pad_token_id=tokenizer.pad_token_id,
        )
        prompt_length = encoded["input_ids"].shape[-1]
        generated_text = tokenizer.decode(output_ids[0][prompt_length:], skip_special_tokens=True)
        return extract_structured_payload(generated_text)

    def doctor(self) -> DoctorStatus:
        settings = get_settings()
        checks = [
            DoctorCheck(
                name="runtime-profile",
                passed=self.runtime_profile == settings.runtime_profile_accelerated,
                detail=f"runtime_profile={self.runtime_profile}",
                remediation_command=ACCELERATED_SETUP_GUIDE,
            )
        ]

        try:
            registry = load_model_registry(
                self.registry_path,
                storage_root=self.storage_root,
            )
        except Exception as exc:
            checks.append(
                DoctorCheck(
                    name="model-registry",
                    passed=False,
                    detail=f"Model registry is unavailable or invalid: {exc}",
                    remediation_command=ACCELERATED_SETUP_GUIDE,
                )
            )
            return DoctorStatus(
                ready=False,
                backend_name=self.backend_name,
                checks=checks,
                setup_steps=[ACCELERATED_SETUP_GUIDE],
            )

        checks.append(
            DoctorCheck(
                name="model-registry",
                passed=True,
                detail="Model registry passed its bounded integrity checks.",
                remediation_command=ACCELERATED_SETUP_GUIDE,
            )
        )
        has_selection = registry.selection is not None
        checks.append(
            DoctorCheck(
                name="pilot-selection",
                passed=has_selection,
                detail="Pilot selection metadata is available." if has_selection else "Pilot selection metadata is missing.",
                remediation_command=ACCELERATED_SETUP_GUIDE,
            )
        )
        if not has_selection:
            return DoctorStatus(
                ready=False,
                backend_name=self.backend_name,
                checks=checks,
                setup_steps=[ACCELERATED_SETUP_GUIDE],
            )

        target_candidate_id = registry.selection.runner_up_id
        adapter_artifact: VerifiedArtifact | None = None
        base_model: VerifiedArtifact | None = None
        artifact_error: Exception | None = None
        try:
            _, adapter_artifact, base_model = self._resolve_runtime_paths()
        except Exception as exc:
            artifact_error = exc
        artifact_ready = adapter_artifact is not None and base_model is not None
        checks.append(
            DoctorCheck(
                name="accelerated-artifact",
                passed=artifact_ready,
                detail=(
                    "Accelerated adapter and base model passed integrity verification."
                    if artifact_ready
                    else f"Accelerated artifacts are unavailable or invalid: {artifact_error}"
                ),
                remediation_command=ACCELERATED_SETUP_GUIDE,
            )
        )

        if artifact_ready:
            try:
                assert adapter_artifact is not None and base_model is not None
                self._load_runtime(
                    adapter_artifact=adapter_artifact,
                    base_model=base_model,
                )
                checks.append(
                    DoctorCheck(
                        name="accelerated-runtime-load",
                        passed=True,
                        detail="Accelerated runtime loaded the verified artifact identity.",
                        remediation_command=ACCELERATED_SETUP_GUIDE,
                    )
                )
            except Exception as exc:
                checks.append(
                    DoctorCheck(
                        name="accelerated-runtime-load",
                        passed=False,
                        detail=f"Accelerated runtime failed to load local resources: {exc}",
                        remediation_command=ACCELERATED_SETUP_GUIDE,
                    )
                )

        ready = all(check.passed for check in checks)
        setup_steps = [] if ready else [ACCELERATED_SETUP_GUIDE]
        return DoctorStatus(
            ready=ready,
            backend_name=self.backend_name,
            checks=checks,
            setup_steps=setup_steps,
        )

    def analyze(self, request: AnalysisRequest) -> AnalysisResult:
        status = self.doctor()
        if not status.ready:
            raise RuntimeError("Accelerated backend is not ready")

        _, adapter_artifact, base_model = self._resolve_runtime_paths()
        runtime = self._load_runtime(
            adapter_artifact=adapter_artifact,
            base_model=base_model,
        )
        payload = self._infer_payload(runtime, request.text)
        return build_analysis_result(payload, request, self.backend_name)
