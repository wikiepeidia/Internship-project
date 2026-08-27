"""Optional accelerated local backend for stronger Phase 3 hardware."""

from __future__ import annotations

import importlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from src.artifacts import find_latest_artifact, load_model_registry
from src.config.settings import get_runtime_settings as get_settings
from src.runtime.analyzers.local_model import (
    build_analysis_result,
    build_structured_analysis_prompt,
    extract_structured_payload,
    resolve_base_model_path,
)
from src.runtime.contracts import AnalysisRequest, AnalysisResult, DoctorCheck, DoctorStatus


ACCELERATED_SETUP_GUIDE = (
    "Install local training extras with python -m pip install -e .[dev,train] and run the Phase 3 training flow for the selected runner-up model."
)


@dataclass
class AcceleratedAnalyzer:
    """Contract-compatible accelerated backend backed by the selected runner-up artifact."""

    registry_path: Path = field(default_factory=lambda: get_settings().model_registry_path)
    runtime_profile: str = field(default_factory=lambda: get_settings().runtime_profile_accelerated)
    backend_name: str = "accelerated"
    _cached_runtime: Any | None = field(default=None, init=False, repr=False)
    _cached_adapter_path: Path | None = field(default=None, init=False, repr=False)
    _cached_base_model_path: Path | None = field(default=None, init=False, repr=False)

    def _resolve_runtime_paths(self) -> tuple[str, Path, Path]:
        settings = get_settings()
        registry = load_model_registry(self.registry_path)
        if registry.selection is None:
            raise RuntimeError("Pilot selection metadata is missing")

        target_candidate_id = registry.selection.runner_up_id
        adapter_artifact = find_latest_artifact(
            registry,
            candidate_id=target_candidate_id,
            artifact_type="adapter",
        )
        if adapter_artifact is None or not adapter_artifact.local_path.exists():
            raise FileNotFoundError(
                f"Missing accelerated adapter artifact for candidate_id={target_candidate_id}"
            )

        base_model_path = resolve_base_model_path(target_candidate_id, settings.model_artifact_root)
        return target_candidate_id, adapter_artifact.local_path, base_model_path

    def _load_runtime(self, *, adapter_path: Path, base_model_path: Path) -> Any:
        if (
            self._cached_runtime is not None
            and self._cached_adapter_path == adapter_path
            and self._cached_base_model_path == base_model_path
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
            trust_remote_code=True,
        )
        if tokenizer.pad_token is None:
            tokenizer.pad_token = tokenizer.eos_token or tokenizer.unk_token

        model_load_kwargs: dict[str, Any] = {
            "local_files_only": True,
            "trust_remote_code": True,
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
        )
        if hasattr(model, "eval"):
            model.eval()

        self._cached_runtime = {
            "model": model,
            "tokenizer": tokenizer,
            "device": "cuda",
        }
        self._cached_adapter_path = adapter_path
        self._cached_base_model_path = base_model_path
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

        if not self.registry_path.exists():
            checks.append(
                DoctorCheck(
                    name="model-registry",
                    passed=False,
                    detail=f"Missing model registry: {self.registry_path}",
                    remediation_command=ACCELERATED_SETUP_GUIDE,
                )
            )
            return DoctorStatus(
                ready=False,
                backend_name=self.backend_name,
                checks=checks,
                setup_steps=[ACCELERATED_SETUP_GUIDE],
            )

        registry = load_model_registry(self.registry_path)
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
        adapter_artifact = find_latest_artifact(
            registry,
            candidate_id=target_candidate_id,
            artifact_type="adapter",
        )
        artifact_ready = adapter_artifact is not None and adapter_artifact.local_path.exists()
        checks.append(
            DoctorCheck(
                name="accelerated-artifact",
                passed=artifact_ready,
                detail=(
                    f"Accelerated artifact ready at {adapter_artifact.local_path}"
                    if artifact_ready
                    else f"Missing accelerated adapter artifact for candidate_id={target_candidate_id}"
                ),
                remediation_command=ACCELERATED_SETUP_GUIDE,
            )
        )

        if artifact_ready:
            try:
                _, adapter_path, base_model_path = self._resolve_runtime_paths()
                self._load_runtime(adapter_path=adapter_path, base_model_path=base_model_path)
                checks.append(
                    DoctorCheck(
                        name="accelerated-runtime-load",
                        passed=True,
                        detail=f"Accelerated runtime can load {adapter_path}",
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

        _, adapter_path, base_model_path = self._resolve_runtime_paths()
        runtime = self._load_runtime(adapter_path=adapter_path, base_model_path=base_model_path)
        payload = self._infer_payload(runtime, request.text)
        return build_analysis_result(payload, request, self.backend_name)
