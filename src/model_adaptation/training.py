"""Training orchestration for Phase 3 adapter builds."""

from __future__ import annotations

import inspect
import importlib
import importlib.util
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from src.config.settings import get_settings
from src.model_adaptation.catalog import get_candidate_by_id
from src.model_adaptation.data import build_training_examples, load_split_records
from src.model_adaptation.registry import build_model_checksum, load_model_registry, save_model_registry
from src.model_adaptation.schemas import ModelArtifactRecord, ModelRegistry, PilotSelection


TrainerCallable = Callable[["TrainingConfig", list[dict[str, Any]], list[dict[str, Any]]], dict[str, Any]]

DEFAULT_TARGET_MODULES: tuple[str, ...] = (
    "q_proj",
    "k_proj",
    "v_proj",
    "o_proj",
    "gate_proj",
    "up_proj",
    "down_proj",
)
SMOKE_TEST_MAX_STEPS = 2


class _TokenizedTextDataset:
    def __init__(self, texts: list[str], tokenizer: Any, max_length: int) -> None:
        self._items = [
            tokenizer(text, truncation=True, max_length=max_length, padding=False)
            for text in texts
        ]

    def __len__(self) -> int:
        return len(self._items)

    def __getitem__(self, index: int) -> dict[str, Any]:
        return self._items[index]


@dataclass(frozen=True)
class TrainingConfig:
    """Resolved training configuration for one selected Phase 3 candidate."""

    candidate_id: str
    baseline_winner_id: str
    runner_up_id: str
    train_split_path: Path
    val_split_path: Path
    version_tag: str
    output_root: Path
    registry_path: Path
    dry_run: bool = False
    base_model_path: Path | None = None
    num_train_epochs: float = 1.0
    max_steps: int = -1
    per_device_train_batch_size: int = 1
    gradient_accumulation_steps: int = 4
    learning_rate: float = 2e-4
    logging_steps: int = 10
    save_steps: int = 50
    save_total_limit: int = 2
    max_seq_length: int = 1024
    smoke_test: bool = False
    resume_from_checkpoint: str | None = None
    device: str = "auto"
    gradient_checkpointing: bool = True
    local_files_only: bool = True
    trust_remote_code: bool = True
    use_4bit: bool = True
    lora_r: int = 16
    lora_alpha: int = 32
    lora_dropout: float = 0.05
    target_modules: tuple[str, ...] = DEFAULT_TARGET_MODULES


def _resolve_selection(selection: PilotSelection | None, registry_path: Path | None) -> PilotSelection:
    if selection is not None:
        return selection
    if registry_path is None:
        raise ValueError("selection or registry_path is required")

    registry = load_model_registry(registry_path)
    if registry.selection is None:
        raise ValueError("Model registry does not contain a pilot selection")
    return registry.selection


def _selected_candidate_ids(selection: PilotSelection) -> set[str]:
    return {selection.baseline_winner_id, selection.runner_up_id}


def build_training_config(
    candidate_id: str,
    train_split_path: Path,
    val_split_path: Path,
    version_tag: str,
    output_root: Path,
    *,
    selection: PilotSelection | None = None,
    registry_path: Path | None = None,
    dry_run: bool = False,
    base_model_path: Path | None = None,
    num_train_epochs: float = 1.0,
    max_steps: int | None = None,
    per_device_train_batch_size: int = 1,
    gradient_accumulation_steps: int = 4,
    learning_rate: float = 2e-4,
    logging_steps: int = 10,
    save_steps: int = 50,
    save_total_limit: int = 2,
    max_seq_length: int = 1024,
    smoke_test: bool = False,
    resume_from_checkpoint: str | None = None,
    device: str = "auto",
    gradient_checkpointing: bool = True,
    local_files_only: bool = True,
    trust_remote_code: bool = True,
    use_4bit: bool = True,
    lora_r: int = 16,
    lora_alpha: int = 32,
    lora_dropout: float = 0.05,
    target_modules: tuple[str, ...] = DEFAULT_TARGET_MODULES,
) -> TrainingConfig:
    """Build a training config restricted to the pilot-selected candidates."""

    resolved_selection = _resolve_selection(selection, registry_path)
    allowed_candidate_ids = _selected_candidate_ids(resolved_selection)
    if candidate_id not in allowed_candidate_ids:
        raise ValueError("Training is limited to the pilot-selected baseline winner and runner-up")

    resolved_registry_path = registry_path or get_settings().model_registry_path
    get_candidate_by_id(candidate_id)
    resolved_max_steps = -1 if max_steps is None else max_steps
    resolved_logging_steps = logging_steps
    resolved_save_steps = save_steps
    resolved_gradient_accumulation_steps = gradient_accumulation_steps
    if smoke_test:
        if max_steps is None or max_steps < 0:
            resolved_max_steps = SMOKE_TEST_MAX_STEPS
        resolved_logging_steps = 1
        resolved_save_steps = 1
        resolved_gradient_accumulation_steps = 1
    return TrainingConfig(
        candidate_id=candidate_id,
        baseline_winner_id=resolved_selection.baseline_winner_id,
        runner_up_id=resolved_selection.runner_up_id,
        train_split_path=train_split_path,
        val_split_path=val_split_path,
        version_tag=version_tag,
        output_root=output_root,
        registry_path=resolved_registry_path,
        dry_run=dry_run,
        base_model_path=base_model_path,
        num_train_epochs=num_train_epochs,
        max_steps=resolved_max_steps,
        per_device_train_batch_size=per_device_train_batch_size,
        gradient_accumulation_steps=resolved_gradient_accumulation_steps,
        learning_rate=learning_rate,
        logging_steps=resolved_logging_steps,
        save_steps=resolved_save_steps,
        save_total_limit=save_total_limit,
        max_seq_length=max_seq_length,
        smoke_test=smoke_test,
        resume_from_checkpoint=resume_from_checkpoint,
        device=device,
        gradient_checkpointing=gradient_checkpointing,
        local_files_only=local_files_only,
        trust_remote_code=trust_remote_code,
        use_4bit=use_4bit,
        lora_r=lora_r,
        lora_alpha=lora_alpha,
        lora_dropout=lora_dropout,
        target_modules=target_modules,
    )


def _candidate_output_dir(config: TrainingConfig) -> Path:
    return config.output_root / config.version_tag / config.candidate_id


def _training_output_dir(config: TrainingConfig) -> Path:
    return _candidate_output_dir(config) / "trainer"


def _adapter_output_dir(config: TrainingConfig) -> Path:
    return _candidate_output_dir(config) / "adapter"


def _load_download_manifest(output_root: Path) -> dict[str, Path]:
    manifest_path = output_root / "manifests" / "download-manifest.json"
    if not manifest_path.exists():
        return {}

    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    model_paths: dict[str, Path] = {}
    for model in payload.get("models", []):
        candidate_id = model.get("candidate_id")
        local_path = model.get("local_path")
        if candidate_id and local_path:
            model_paths[str(candidate_id)] = Path(str(local_path))
    return model_paths


def _resolve_base_model_path(config: TrainingConfig) -> Path:
    if config.base_model_path is not None:
        if config.base_model_path.exists():
            return config.base_model_path
        raise FileNotFoundError(f"Missing base model path: {config.base_model_path}")

    manifest_model_paths = _load_download_manifest(config.output_root)
    manifest_path = manifest_model_paths.get(config.candidate_id)
    if manifest_path is not None and manifest_path.exists():
        return manifest_path

    fallback_path = config.output_root / "base" / config.candidate_id
    if fallback_path.exists():
        return fallback_path

    raise FileNotFoundError(
        f"Missing base model for candidate_id={config.candidate_id}. "
        f"Expected {config.output_root / 'manifests' / 'download-manifest.json'} or {fallback_path}"
    )


def _build_supervised_text(example: dict[str, Any]) -> str:
    return "\n\n".join(
        [
            "### Instruction",
            str(example["prompt"]),
            "### Response",
            str(example["response"]),
        ]
    )


def _import_training_stack() -> tuple[Any, Any, Any]:
    modules: dict[str, Any] = {}
    missing_modules: list[str] = []
    for module_name in ("torch", "transformers", "peft", "accelerate"):
        try:
            modules[module_name] = importlib.import_module(module_name)
        except ImportError:
            missing_modules.append(module_name)

    if missing_modules:
        missing = ", ".join(missing_modules)
        raise RuntimeError(
            f"Missing training dependencies: {missing}. "
            "Install them with python -m pip install -e .[dev,train]"
        )
    return modules["torch"], modules["transformers"], modules["peft"]


def _resolve_device(torch_module: Any, requested_device: str) -> str:
    if requested_device == "auto":
        return "cuda" if torch_module.cuda.is_available() else "cpu"
    if requested_device == "cuda" and not torch_module.cuda.is_available():
        raise RuntimeError("CUDA was requested for training, but torch.cuda.is_available() is false")
    if requested_device not in {"cpu", "cuda"}:
        raise ValueError("device must be one of: auto, cpu, cuda")
    return requested_device


def _resolve_torch_dtype(torch_module: Any, device: str) -> Any:
    if device == "cuda":
        return torch_module.bfloat16 if torch_module.cuda.is_bf16_supported() else torch_module.float16
    return torch_module.float32


def _resolve_quantization_config(transformers_module: Any, torch_module: Any, config: TrainingConfig, device: str) -> tuple[Any | None, str]:
    if not config.use_4bit or device != "cuda" or importlib.util.find_spec("bitsandbytes") is None:
        return None, "full-precision-lora"
    if not hasattr(transformers_module, "BitsAndBytesConfig"):
        return None, "full-precision-lora"

    compute_dtype = _resolve_torch_dtype(torch_module, device)
    quantization_config = transformers_module.BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_compute_dtype=compute_dtype,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_use_double_quant=True,
    )
    return quantization_config, "4bit-qlora"


def _latest_checkpoint_path(training_output_dir: Path) -> Path | None:
    checkpoints = [path for path in training_output_dir.glob("checkpoint-*") if path.is_dir()]
    if not checkpoints:
        return None
    return sorted(
        checkpoints,
        key=lambda path: (
            int(path.name.split("-")[-1]) if path.name.split("-")[-1].isdigit() else -1,
            path.name,
        ),
    )[-1]


def _resolve_resume_checkpoint(config: TrainingConfig, training_output_dir: Path) -> Path | None:
    if not config.resume_from_checkpoint:
        return None
    if config.resume_from_checkpoint == "latest":
        latest_checkpoint = _latest_checkpoint_path(training_output_dir)
        if latest_checkpoint is None:
            raise FileNotFoundError(f"No checkpoint directories found under {training_output_dir}")
        return latest_checkpoint

    resume_path = Path(config.resume_from_checkpoint)
    if not resume_path.exists():
        raise FileNotFoundError(f"Missing checkpoint path: {resume_path}")
    return resume_path


def _json_ready(value: Any) -> Any:
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {key: _json_ready(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_json_ready(item) for item in value]
    return value


def _build_training_arguments(
    transformers_module: Any,
    config: TrainingConfig,
    training_output_dir: Path,
    *,
    has_eval_data: bool,
    device: str,
    use_bf16: bool,
) -> Any:
    parameter_names = set(inspect.signature(transformers_module.TrainingArguments.__init__).parameters)
    training_kwargs: dict[str, Any] = {
        "output_dir": str(training_output_dir),
        "num_train_epochs": config.num_train_epochs,
        "max_steps": config.max_steps,
        "per_device_train_batch_size": config.per_device_train_batch_size,
        "per_device_eval_batch_size": 1,
        "gradient_accumulation_steps": config.gradient_accumulation_steps,
        "learning_rate": config.learning_rate,
        "logging_steps": config.logging_steps,
        "save_steps": config.save_steps,
        "save_total_limit": config.save_total_limit,
        "eval_steps": config.save_steps if has_eval_data else None,
        "remove_unused_columns": False,
        "report_to": [],
        "logging_first_step": True,
        "save_safetensors": True,
        "dataloader_pin_memory": device == "cuda",
        "fp16": device == "cuda" and not use_bf16,
        "bf16": use_bf16,
        "gradient_checkpointing": config.gradient_checkpointing,
    }
    if "eval_strategy" in parameter_names:
        training_kwargs["eval_strategy"] = "steps" if has_eval_data else "no"
    elif "evaluation_strategy" in parameter_names:
        training_kwargs["evaluation_strategy"] = "steps" if has_eval_data else "no"

    if "use_cpu" in parameter_names:
        training_kwargs["use_cpu"] = device == "cpu"
    elif "no_cuda" in parameter_names:
        training_kwargs["no_cuda"] = device == "cpu"

    if "overwrite_output_dir" in parameter_names:
        training_kwargs["overwrite_output_dir"] = False

    supported_kwargs = {
        key: value
        for key, value in training_kwargs.items()
        if key in parameter_names and value is not None
    }
    return transformers_module.TrainingArguments(**supported_kwargs)


def _run_local_adapter_training(
    config: TrainingConfig,
    train_examples: list[dict[str, Any]],
    val_examples: list[dict[str, Any]],
) -> dict[str, Any]:
    torch_module, transformers_module, peft_module = _import_training_stack()

    base_model_path = _resolve_base_model_path(config)
    device = _resolve_device(torch_module, config.device)
    training_output_dir = _training_output_dir(config)
    training_output_dir.mkdir(parents=True, exist_ok=True)
    adapter_output_dir = _adapter_output_dir(config)
    adapter_output_dir.mkdir(parents=True, exist_ok=True)
    resume_checkpoint = _resolve_resume_checkpoint(config, training_output_dir)

    tokenizer = transformers_module.AutoTokenizer.from_pretrained(
        str(base_model_path),
        local_files_only=config.local_files_only,
        trust_remote_code=config.trust_remote_code,
    )
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token or tokenizer.unk_token
    tokenizer.padding_side = "right"

    quantization_config, quantization_mode = _resolve_quantization_config(
        transformers_module,
        torch_module,
        config,
        device,
    )
    model_load_kwargs: dict[str, Any] = {
        "local_files_only": config.local_files_only,
        "trust_remote_code": config.trust_remote_code,
        "low_cpu_mem_usage": True,
    }
    if quantization_config is not None:
        model_load_kwargs["quantization_config"] = quantization_config
        model_load_kwargs["device_map"] = {"": 0}
    else:
        model_load_kwargs["torch_dtype"] = _resolve_torch_dtype(torch_module, device)

    model = transformers_module.AutoModelForCausalLM.from_pretrained(
        str(base_model_path),
        **model_load_kwargs,
    )
    if config.gradient_checkpointing and hasattr(model, "gradient_checkpointing_enable"):
        model.gradient_checkpointing_enable()
        if hasattr(model, "config"):
            model.config.use_cache = False
    if quantization_config is not None and hasattr(peft_module, "prepare_model_for_kbit_training"):
        model = peft_module.prepare_model_for_kbit_training(model)

    lora_config = peft_module.LoraConfig(
        r=config.lora_r,
        lora_alpha=config.lora_alpha,
        lora_dropout=config.lora_dropout,
        bias="none",
        task_type="CAUSAL_LM",
        target_modules=list(config.target_modules),
    )
    model = peft_module.get_peft_model(model, lora_config)
    if tokenizer.pad_token_id is not None and getattr(model.config, "pad_token_id", None) is None:
        model.config.pad_token_id = tokenizer.pad_token_id

    train_dataset = _TokenizedTextDataset(
        [_build_supervised_text(example) for example in train_examples],
        tokenizer,
        config.max_seq_length,
    )
    eval_dataset = _TokenizedTextDataset(
        [_build_supervised_text(example) for example in val_examples],
        tokenizer,
        config.max_seq_length,
    )

    use_bf16 = device == "cuda" and torch_module.cuda.is_bf16_supported()
    training_args = _build_training_arguments(
        transformers_module,
        config,
        training_output_dir,
        has_eval_data=len(eval_dataset) > 0,
        device=device,
        use_bf16=use_bf16,
    )
    trainer = transformers_module.Trainer(
        model=model,
        args=training_args,
        train_dataset=train_dataset,
        eval_dataset=eval_dataset if len(eval_dataset) else None,
        data_collator=transformers_module.DataCollatorForLanguageModeling(
            tokenizer=tokenizer,
            mlm=False,
        ),
    )

    try:
        train_result = trainer.train(
            resume_from_checkpoint=(str(resume_checkpoint) if resume_checkpoint is not None else None)
        )
    except RuntimeError as exc:
        if "out of memory" in str(exc).casefold():
            raise RuntimeError(
                "Local training ran out of memory. Retry with --smoke-test, a smaller batch size, "
                "or resume later with --resume-from-checkpoint latest."
            ) from exc
        raise

    model.save_pretrained(str(adapter_output_dir))
    tokenizer.save_pretrained(str(adapter_output_dir))
    trainer.save_state()

    latest_checkpoint = _latest_checkpoint_path(training_output_dir)
    training_summary = {
        "candidate_id": config.candidate_id,
        "base_model_path": base_model_path,
        "device": device,
        "quantization_mode": quantization_mode,
        "resume_from_checkpoint": resume_checkpoint,
        "checkpoint_path": latest_checkpoint,
        "smoke_test": config.smoke_test,
        "train_examples": len(train_examples),
        "val_examples": len(val_examples),
        "metrics": train_result.metrics,
    }
    summary_path = adapter_output_dir / "training-summary.json"
    summary_path.write_text(
        json.dumps(_json_ready(training_summary), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return {
        "artifact_path": adapter_output_dir,
        "base_model_path": base_model_path,
        "device": device,
        "quantization_mode": quantization_mode,
        "resume_from_checkpoint": resume_checkpoint,
        "checkpoint_path": latest_checkpoint,
        "summary_path": summary_path,
    }


def save_adapter_artifacts(
    config: TrainingConfig,
    *,
    selection: PilotSelection | None = None,
    artifact_source_path: Path | None = None,
    artifact_bytes: bytes | None = None,
) -> ModelArtifactRecord:
    """Stage one adapter artifact and register its metadata locally."""

    resolved_selection = _resolve_selection(selection, config.registry_path)
    candidate_dir = config.output_root / config.version_tag / config.candidate_id
    candidate_dir.mkdir(parents=True, exist_ok=True)

    artifact_path = artifact_source_path or (candidate_dir / "adapter-placeholder.bin")
    if artifact_source_path is None:
        payload = artifact_bytes or json.dumps(
            {
                "candidate_id": config.candidate_id,
                "version_tag": config.version_tag,
                "mode": "dry-run" if config.dry_run else "staged",
            },
            ensure_ascii=False,
            indent=2,
        ).encode("utf-8")
        artifact_path.write_bytes(payload)

    artifact_record = ModelArtifactRecord(
        candidate_id=config.candidate_id,
        artifact_type="adapter",
        version_tag=config.version_tag,
        local_path=artifact_path,
        sha256=build_model_checksum(artifact_path),
        profile_name="baseline-winner" if config.candidate_id == resolved_selection.baseline_winner_id else "runner-up",
    )

    if config.registry_path.exists():
        registry = load_model_registry(config.registry_path)
    else:
        registry = ModelRegistry(version_tag=config.version_tag, selection=resolved_selection)

    registry.selection = resolved_selection
    registry.version_tag = config.version_tag
    registry.artifacts = [
        existing
        for existing in registry.artifacts
        if not (
            existing.candidate_id == artifact_record.candidate_id
            and existing.artifact_type == artifact_record.artifact_type
            and existing.version_tag == artifact_record.version_tag
        )
    ]
    registry.artifacts.append(artifact_record)
    save_model_registry(registry, config.registry_path)
    return artifact_record


def run_training(
    config: TrainingConfig,
    *,
    selection: PilotSelection | None = None,
    trainer: TrainerCallable | None = None,
) -> dict[str, Any]:
    """Run a dry-run validation or delegate to a pluggable trainer callable."""

    resolved_selection = _resolve_selection(selection, config.registry_path if config.registry_path.exists() else None)
    if config.candidate_id not in _selected_candidate_ids(resolved_selection):
        raise ValueError("Training is limited to the pilot-selected baseline winner and runner-up")

    candidate = get_candidate_by_id(config.candidate_id)
    train_records = load_split_records(config.train_split_path)
    val_records = load_split_records(config.val_split_path)
    train_examples = build_training_examples(train_records, candidate)
    val_examples = build_training_examples(val_records, candidate)

    if config.dry_run:
        artifact_record = save_adapter_artifacts(config, selection=resolved_selection)
        return {
            "dry_run": True,
            "candidate_id": config.candidate_id,
            "train_examples": len(train_examples),
            "val_examples": len(val_examples),
            "artifact_record": artifact_record,
        }

    trainer_result = (
        trainer(config, train_examples, val_examples)
        if trainer is not None
        else _run_local_adapter_training(config, train_examples, val_examples)
    )
    artifact_record = save_adapter_artifacts(
        config,
        selection=resolved_selection,
        artifact_source_path=Path(trainer_result["artifact_path"]),
    )
    result = {
        "dry_run": False,
        "candidate_id": config.candidate_id,
        "train_examples": len(train_examples),
        "val_examples": len(val_examples),
        "artifact_record": artifact_record,
    }
    result.update({key: value for key, value in trainer_result.items() if key != "artifact_path"})
    return result