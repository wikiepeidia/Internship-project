# ============================================================
# STEP 5 of 10 — QLoRA Fine-Tuning
# ============================================================
# Canonical source (this numbered copy exists ONLY for defense-day
# navigation — it is not a second implementation and is not imported
# by anything): src/model_adaptation/training.py
#
# What this file does: TrainingConfig (line ~48) holds every real
# hyperparameter — lora_r=16, lora_alpha=32, lora_dropout=0.05,
# target_modules=DEFAULT_TARGET_MODULES (7 attention+MLP projections),
# batch=1, grad-accum=4, lr=2e-4, 1 epoch. run_training() loads the
# base model (optionally 4-bit NF4-quantized), wraps it with
# peft.LoraConfig, and runs transformers.Trainer.train(). Saves the
# adapter + training-summary.json and registers it in the local
# model registry, which step 6 and step 10 both read from.
#
# See also: documents/reports/supervisor/defense_code_navigation.md
# ============================================================

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

# THE 7 LoRA TARGET MODULES. This is the "why some parameters" answer for
# target_modules specifically: a transformer decoder block has attention
# projections (q_proj/k_proj/v_proj/o_proj — query/key/value/output) AND
# MLP projections (gate_proj/up_proj/down_proj, the feed-forward network).
# Applying LoRA adapters to ONLY q_proj/v_proj (a common minimal choice in
# a lot of LoRA tutorials) saves memory but limits what the adapter can
# actually learn — it can only reshape attention, not the feed-forward
# reasoning. All 7 here means the adapter can adjust both HOW the model
# attends to tokens and HOW it processes/transforms them afterward, which
# matters for a task like this (classifying nuanced threat categories) that
# needs more than just an attention-pattern shift. The cost: more trainable
# parameters than a minimal target_modules set — a deliberate quality-over-
# minimal-footprint tradeoff, offset by using 4-bit quantization
# (use_4bit below) to keep the overall memory budget in check anyway.
DEFAULT_TARGET_MODULES: tuple[str, ...] = (
    "q_proj",
    "k_proj",
    "v_proj",
    "o_proj",
    "gate_proj",
    "up_proj",
    "down_proj",
)
SMOKE_TEST_MAX_STEPS = 2   # smoke_test mode: just prove the training loop RUNS end-to-end, don't actually train


class _TokenizedTextDataset:
    """
    Minimal PyTorch-Dataset-shaped wrapper (just needs __len__ and
    __getitem__) around a list of already-tokenized examples. Tokenizes
    EAGERLY in __init__ (all at once, up front) rather than lazily per
    __getitem__ call — fine here because the dataset sizes involved are
    small enough (thousands of short messages, not millions) that
    pre-tokenizing everything into memory isn't a problem, and it keeps
    __getitem__ trivially fast during actual training steps.
    """
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
    """
    Resolved training configuration for one selected Phase 3 candidate.

    THIS IS WHERE EVERY REAL HYPERPARAMETER LIVES — if asked "why r=16,
    why alpha=32, why dropout=0.05" this is the class to open and point at.
    The QLoRA-specific ones, with the reasoning behind each:

      - lora_r=16: the LoRA "rank" — the inner dimension of the two small
        low-rank matrices that get trained instead of the full weight
        matrix. Bigger r = more trainable capacity but more parameters/
        memory; 16 is a well-established middle-ground value in the QLoRA
        literature — enough capacity to learn a focused classification/
        extraction task without approaching full-finetune parameter counts.
      - lora_alpha=32: the LoRA scaling factor, applied as alpha/r to the
        adapter's output before adding it back to the frozen base weights.
        alpha=32 with r=16 gives a scaling factor of exactly 2 — a common,
        stable convention (alpha = 2x r) that keeps the adapter's
        contribution meaningfully sized relative to the frozen base weights
        without overpowering them early in training.
      - lora_dropout=0.05: a small amount of dropout applied inside the
        adapter path during training, as light regularization against
        overfitting — kept small (5%, not e.g. 20-30%) because the adapter
        itself is already low-capacity (rank 16), so it doesn't need heavy
        regularization on top; a little is enough to discourage memorizing
        the ~2000-example training set outright.
      - target_modules: see DEFAULT_TARGET_MODULES comment above — all 7
        attention+MLP projections, not just attention.
      - use_4bit=True: this is QLoRA proper (Q = quantized) — the FROZEN
        base model is loaded in 4-bit (NF4) during training to fit
        available GPU memory, while the small LoRA adapter matrices
        themselves are still trained in higher precision. This 4-bit
        TRAINING-time quantization is a completely separate thing from the
        8-bit (Q8_0) quantization applied later at step 6 for the CPU
        deployment artifact — different bit-widths for different reasons
        (fit training on limited hardware vs. balance size/quality for
        local CPU inference). Mixing these up is a common Q&A trap.
      - per_device_train_batch_size=1, gradient_accumulation_steps=4:
        effective batch size of 4 (1 x 4) achieved via accumulation rather
        than a literal batch of 4 — this is what fits in memory on the
        available training hardware; accumulating 4 micro-batches before
        each optimizer step approximates the gradient quality of a real
        batch-of-4 without needing 4x the memory at once. (This is also the
        basis of the live checkpoint-count sanity check: total training
        examples ÷ (batch_size x grad_accum_steps) ≈ expected step count —
        see the Q&A prep doc §4 for the exact derivable numbers.)
      - learning_rate=2e-4: a typical LoRA learning rate — notably higher
        than a full-finetune learning rate (which is usually ~1e-5 to
        2e-5), because only the small adapter matrices are being updated,
        not the full pretrained weights, so a larger step size is both safe
        and necessary to make meaningful progress in a small number of
        steps/1 epoch.
      - num_train_epochs=1.0: a single pass over the training data — kept
        to one epoch deliberately given the dataset size (~2000 examples
        after judging/splitting) to avoid overfitting a small dataset by
        cycling over it repeatedly.
    """

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
    # PilotSelection comes from the EARLIER pilot stage (src/model_adaptation/
    # pilot.py — scores 3 candidate base models on a small recall-weighted
    # benchmark before any fine-tuning happens at all). This function's job
    # is just "find that decision, wherever it's recorded" — either passed
    # in directly, or read back out of the persisted model registry JSON on
    # disk if not.
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

    # HARD GATE: you cannot fine-tune just any random base model — it has
    # to be one of the two the pilot stage already identified as worth the
    # investment (the winner + a runner-up, kept as a second option). This
    # is a deliberate process guardrail against accidentally burning a full
    # training run on a candidate that never earned it via the pilot
    # comparison.
    resolved_selection = _resolve_selection(selection, registry_path)
    allowed_candidate_ids = _selected_candidate_ids(resolved_selection)
    if candidate_id not in allowed_candidate_ids:
        raise ValueError("Training is limited to the pilot-selected baseline winner and runner-up")

    resolved_registry_path = registry_path or get_settings().model_registry_path
    get_candidate_by_id(candidate_id)  # raises if candidate_id isn't a real known catalog entry — fail fast before any real work
    resolved_max_steps = -1 if max_steps is None else max_steps
    resolved_logging_steps = logging_steps
    resolved_save_steps = save_steps
    resolved_gradient_accumulation_steps = gradient_accumulation_steps
    if smoke_test:
        # smoke_test mode overrides several fields to make a training run
        # finish in seconds instead of hours: cap at just 2 steps
        # (SMOKE_TEST_MAX_STEPS), log/save every single step (so you can
        # SEE it's actually progressing), and drop gradient accumulation to
        # 1 (skip the accumulation wait entirely). Purpose: verify the
        # whole training pipeline (model loading, quantization, LoRA
        # wrapping, the Trainer loop, artifact saving) actually WORKS
        # end-to-end on this machine before committing to a real multi-hour
        # run — catches environment/dependency/path problems cheaply.
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
    # output_root / version_tag / candidate_id — a predictable, three-level
    # directory convention every other path helper below builds on, so
    # results from different candidates and different versioned runs never
    # collide on disk.
    return config.output_root / config.version_tag / config.candidate_id


def _training_output_dir(config: TrainingConfig) -> Path:
    return _candidate_output_dir(config) / "trainer"  # raw HF Trainer state: checkpoint-N dirs, logs


def _adapter_output_dir(config: TrainingConfig) -> Path:
    return _candidate_output_dir(config) / "adapter"  # the final, clean adapter artifact — what gets registered/consumed downstream


def _load_download_manifest(output_root: Path) -> dict[str, Path]:
    # Base models are downloaded separately (a distinct pipeline stage, not
    # shown in this numbered walkthrough) and recorded in this manifest —
    # candidate_id -> local filesystem path. Missing manifest file is
    # treated as "no entries" rather than an error, since
    # _resolve_base_model_path below has further fallbacks to try first.
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
    # Three-tier lookup, in priority order: (1) an EXPLICIT base_model_path
    # on the config always wins if set and actually exists, (2) otherwise
    # check the download manifest for this candidate_id, (3) otherwise try
    # a conventional fallback location (output_root/base/candidate_id).
    # Only raises if ALL THREE come up empty — gives the caller a clear
    # error message listing exactly where it looked, rather than a bare
    # "file not found."
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
    # The instruction-tuning template every training example gets rendered
    # into before tokenization — a plain "### Instruction / ### Response"
    # convention. Simple and explicit on purpose: the model just needs a
    # consistent, learnable marker for "here's the input, here's the
    # expected output," and this two-section format is one of the most
    # common, well-understood conventions for that in the open fine-tuning
    # ecosystem.
    return "\n\n".join(
        [
            "### Instruction",
            str(example["prompt"]),
            "### Response",
            str(example["response"]),
        ]
    )


def _import_training_stack() -> tuple[Any, Any, Any]:
    # Heavy training-only dependencies (torch, transformers, peft,
    # accelerate) are imported lazily HERE, not at module top — this whole
    # training.py module can still be imported (e.g. by other code that
    # just wants TrainingConfig or build_training_config) on a machine that
    # doesn't have the full training stack installed; you only hit this
    # hard failure if you actually try to RUN training without the
    # dependencies present.
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
    # "auto" (the default) picks CUDA if a GPU is actually available,
    # otherwise falls back to CPU — so the exact same TrainingConfig can be
    # used unchanged on whatever machine happens to be running it. Explicit
    # "cuda" fails LOUDLY if no GPU is actually present rather than
    # silently falling back — if you asked for GPU training specifically,
    # silently downgrading to CPU (which would be dramatically slower and
    # easy not to notice) is the wrong failure mode.
    if requested_device == "auto":
        return "cuda" if torch_module.cuda.is_available() else "cpu"
    if requested_device == "cuda" and not torch_module.cuda.is_available():
        raise RuntimeError("CUDA was requested for training, but torch.cuda.is_available() is false")
    if requested_device not in {"cpu", "cuda"}:
        raise ValueError("device must be one of: auto, cpu, cuda")
    return requested_device


def _resolve_torch_dtype(torch_module: Any, device: str) -> Any:
    # On GPU, prefer bfloat16 over float16 when the GPU supports it (bf16
    # has the same exponent range as float32, so it's much less prone to
    # the overflow/underflow issues float16 can hit during training) —
    # float16 is only the fallback for GPUs that don't support bf16. CPU
    # training always uses full float32 — CPUs don't get meaningful speed
    # benefits from half-precision the way GPU tensor cores do.
    if device == "cuda":
        return torch_module.bfloat16 if torch_module.cuda.is_bf16_supported() else torch_module.float16
    return torch_module.float32


def _resolve_quantization_config(transformers_module: Any, torch_module: Any, config: TrainingConfig, device: str) -> tuple[Any | None, str]:
    """
    Decides whether this training run actually gets the "Q" in QLoRA
    (4-bit-quantized frozen base weights) or falls back to plain
    full-precision LoRA. Three separate conditions can each independently
    disable 4-bit quantization: (1) config.use_4bit=False (explicit
    opt-out), (2) device != "cuda" (bitsandbytes 4-bit quantization is a
    CUDA-only technique — there's no meaningful CPU equivalent, so training
    on CPU always means full precision), (3) the `bitsandbytes` package
    isn't installed at all. Any ONE of these silently and gracefully
    degrades to "full-precision-lora" mode rather than crashing — meaning
    this exact same function can be run on a CUDA machine with
    bitsandbytes (gets real QLoRA) or a CPU-only dev machine (gets slower
    but still-correct full-precision LoRA) without any code changes,
    useful for local testing before a real GPU training run.
    """
    if not config.use_4bit or device != "cuda" or importlib.util.find_spec("bitsandbytes") is None:
        return None, "full-precision-lora"
    if not hasattr(transformers_module, "BitsAndBytesConfig"):
        return None, "full-precision-lora"

    compute_dtype = _resolve_torch_dtype(torch_module, device)
    # NF4 ("NormalFloat4") — the specific 4-bit format QLoRA's paper
    # introduced, tuned for how pretrained weights are actually
    # distributed (roughly normal/Gaussian), which preserves more accuracy
    # than a naive uniform 4-bit quantization would at the same bit-width.
    # bnb_4bit_use_double_quant=True: quantizes the quantization CONSTANTS
    # themselves a second time — a further memory-saving trick from the
    # same QLoRA paper, small additional savings with negligible accuracy
    # cost. bnb_4bit_compute_dtype: even though weights are STORED in 4-bit,
    # the actual matrix-multiply math happens by dequantizing on-the-fly
    # into this higher-precision compute_dtype (bf16/fp16) — 4-bit is a
    # storage/memory optimization, not a computation-precision one.
    quantization_config = transformers_module.BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_compute_dtype=compute_dtype,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_use_double_quant=True,
    )
    return quantization_config, "4bit-qlora"


def _latest_checkpoint_path(training_output_dir: Path) -> Path | None:
    # HuggingFace Trainer writes checkpoint directories named
    # "checkpoint-<step_number>" — sort by the NUMERIC step suffix (not
    # alphabetically, which would incorrectly order "checkpoint-100" before
    # "checkpoint-20"), and this is also exactly the number the live
    # checkpoint-count sanity check in Q&A prep uses: total training
    # examples ÷ (per_device_train_batch_size x gradient_accumulation_steps)
    # tells you roughly how many total optimizer steps 1 epoch takes,
    # which should line up with the highest checkpoint-N folder that
    # exists on disk after a completed run.
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
    # Three states for resume_from_checkpoint: None (fresh start, no
    # resume), the literal string "latest" (auto-find the most recent
    # checkpoint-N dir via the helper above), or an explicit path (resume
    # from a SPECIFIC checkpoint, e.g. to roll back a few steps after
    # noticing a problem partway through). "latest" existing but no
    # checkpoints found on disk is treated as an error, not a silent no-op
    # — if the user asked to resume, silently starting fresh instead would
    # be a confusing, easy-to-miss surprise.
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
    # Recursively converts Path objects (which json.dumps can't serialize
    # natively) to plain strings anywhere they appear, including nested
    # inside dicts/lists — used just before writing training-summary.json,
    # since several fields in that summary (base_model_path,
    # checkpoint_path, etc.) are Path objects internally.
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
    # WHY inspect the constructor's parameter names at all, instead of just
    # building TrainingArguments(**training_kwargs) directly: the
    # `transformers` library has renamed a couple of TrainingArguments
    # fields across versions (eval_strategy vs the older
    # evaluation_strategy; use_cpu vs the older no_cuda). Introspecting the
    # actual installed version's __init__ signature and only passing
    # kwargs it recognizes means this code keeps working across a range of
    # transformers versions without needing a hard pin to one exact
    # release — a version-compatibility shim, not defensive-for-no-reason.
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
    """
    THE ACTUAL TRAINING FUNCTION — everything above this in the file exists
    to prepare inputs for, or persist outputs from, this one function. Walk
    it top to bottom if asked "how does training actually run, in code":
      1. Import the heavy ML stack, resolve where the base model lives on
         disk and which device (cuda/cpu) to use.
      2. Load the tokenizer, make sure it HAS a pad token (some base models
         ship without one defined) — needed because training batches
         (even batch size 1 with accumulation) require padding to align
         sequence lengths.
      3. Decide on 4-bit quantization (see _resolve_quantization_config)
         and load the base model accordingly.
      4. If quantized, run prepare_model_for_kbit_training — this is a
         required peft step that does things like casting layer norms to
         float32 and enabling input gradients so training a quantized
         model actually works correctly, not just loads.
      5. Wrap the model with the LoraConfig (this is where lora_r=16,
         lora_alpha=32, lora_dropout=0.05, and the 7 target_modules from
         TrainingConfig actually get consumed) via get_peft_model — AFTER
         this call, only the small adapter matrices have requires_grad=True;
         every original base-model weight stays frozen.
      6. Build tokenized train/eval datasets, build TrainingArguments, hand
         everything to a standard HuggingFace Trainer, and call .train().
      7. Save the adapter (NOT the full model — just the small LoRA
         weights, tiny compared to the multi-GB base model), save
         tokenizer + trainer state, and write training-summary.json (the
         file that has the real metrics, checkpoint path, and example
         counts for whatever training run just happened).
    """
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
        # Some base models (esp. LLaMA-family) don't define a pad token by
        # default — fall back to eos_token first (a common, safe
        # convention for causal LMs), then unk_token as a last resort if
        # even that's missing.
        tokenizer.pad_token = tokenizer.eos_token or tokenizer.unk_token
    tokenizer.padding_side = "right"  # standard for causal LM training (as opposed to "left", which generation-time batching sometimes prefers)

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
        model_load_kwargs["device_map"] = {"": 0}  # pin the whole (quantized) model onto GPU 0 — no multi-GPU sharding here
    else:
        model_load_kwargs["torch_dtype"] = _resolve_torch_dtype(torch_module, device)

    model = transformers_module.AutoModelForCausalLM.from_pretrained(
        str(base_model_path),
        **model_load_kwargs,
    )
    if config.gradient_checkpointing and hasattr(model, "gradient_checkpointing_enable"):
        # Gradient checkpointing trades compute for memory: instead of
        # keeping every layer's activations in memory for the backward
        # pass, it recomputes them on the fly — slower per step, but
        # meaningfully lowers peak memory, which matters a lot when
        # training on constrained hardware. use_cache=False is REQUIRED
        # alongside this — the KV-cache (normally a generation-speed
        # optimization) is incompatible with recomputing activations
        # during the backward pass.
        model.gradient_checkpointing_enable()
        if hasattr(model, "config"):
            model.config.use_cache = False
    if quantization_config is not None and hasattr(peft_module, "prepare_model_for_kbit_training"):
        # Required peft preprocessing step for k-bit (4-bit here) training:
        # among other things, upcasts LayerNorm to float32 for numerical
        # stability and makes sure input embeddings require grad so
        # gradients can actually flow into the (otherwise frozen,
        # quantized) base model far enough to reach the LoRA adapters.
        model = peft_module.prepare_model_for_kbit_training(model)

    # THE LoRA WRAP — this is the exact line where lora_r/lora_alpha/
    # lora_dropout/target_modules from TrainingConfig get turned into an
    # actual adapter. bias="none": don't add trainable bias terms (only
    # adapt the weight matrices) — the standard, most memory-efficient
    # LoRA convention. task_type="CAUSAL_LM": tells peft this is a
    # next-token-prediction model (as opposed to e.g. seq2seq or
    # classification-head architectures), which affects how it wires up
    # the adapters internally.
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

    # _build_supervised_text (below) formats every example into an
    # "### Instruction\n...\n### Response\n..." block BEFORE tokenizing —
    # this is standard instruction-tuning format, giving the model a
    # consistent structural cue for where the prompt ends and the expected
    # response begins.
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
        # DataCollatorForLanguageModeling with mlm=False: standard causal
        # (next-token prediction) collation, NOT masked-language-modeling
        # (mlm=True is the BERT-style objective) — this model is trained to
        # predict the next token left-to-right, matching how it's actually
        # used at inference time.
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
        # Specifically catch CUDA OOM and re-raise with an ACTIONABLE
        # message (try smoke-test / smaller batch / resume from checkpoint)
        # rather than letting the raw, often cryptic torch OOM traceback be
        # the only thing the caller sees. Any OTHER RuntimeError (not OOM)
        # just propagates unchanged — this isn't a blanket catch-and-hide.
        if "out of memory" in str(exc).casefold():
            raise RuntimeError(
                "Local training ran out of memory. Retry with --smoke-test, a smaller batch size, "
                "or resume later with --resume-from-checkpoint latest."
            ) from exc
        raise

    # save_pretrained on a peft-wrapped model saves ONLY the small adapter
    # weights (a few/tens of MB), not the multi-GB base model — the base
    # model is expected to still be available separately (via
    # base_model_path) whenever this adapter is loaded again, e.g. by
    # convert.py in step 6.
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
    """
    Stage one adapter artifact and register its metadata locally.

    This is the function that turns "some files on disk" into a tracked,
    checksummed entry in the LOCAL MODEL REGISTRY — the same registry
    step 6 (convert.py) reads to find the adapter to merge, and step 10
    (the GGUF backend) ultimately traces back to for provenance. Two modes:
    if artifact_source_path is given (the real training path, pointing at
    wherever _run_local_adapter_training actually saved the adapter), that
    real file is registered. If not (the dry_run path, used to validate
    the whole plumbing — config, registry, data loading — without spending
    hours on actual GPU training), a small placeholder JSON blob is written
    and registered instead, so dry-run and real runs exercise the exact
    same registration code path.
    """

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
        # SHA256 checksum of the actual artifact bytes — this is what
        # makes any reported result TRACEABLE: given a training-summary.json
        # or a report figure, you can verify it came from exactly this
        # artifact and not a different, possibly-stale one.
        sha256=build_model_checksum(artifact_path),
        profile_name="baseline-winner" if config.candidate_id == resolved_selection.baseline_winner_id else "runner-up",
    )

    if config.registry_path.exists():
        registry = load_model_registry(config.registry_path)
    else:
        registry = ModelRegistry(version_tag=config.version_tag, selection=resolved_selection)

    registry.selection = resolved_selection
    registry.version_tag = config.version_tag
    # Replace-not-duplicate: strip out any EXISTING entry for this exact
    # (candidate_id, artifact_type, version_tag) triple before appending
    # the new one. Makes re-running training for the same candidate/version
    # idempotent in the registry — you get one current entry per triple,
    # not an ever-growing list of stale duplicates from repeated runs.
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
    """
    Run a dry-run validation or delegate to a pluggable trainer callable.

    THE TOP-LEVEL PUBLIC ENTRY POINT for this whole module — this is what
    a CLI command or calling script actually invokes. Re-validates the
    pilot-selection gate one more time here (same check as
    build_training_config) since config could technically be constructed
    by hand rather than always going through that builder. `trainer` is an
    injectable callable — mainly a testing seam so unit tests can substitute
    a fake trainer function instead of running real GPU training; when not
    provided (the normal/production case) it defaults to
    _run_local_adapter_training, the real implementation covered above.
    """

    resolved_selection = _resolve_selection(selection, config.registry_path if config.registry_path.exists() else None)
    if config.candidate_id not in _selected_candidate_ids(resolved_selection):
        raise ValueError("Training is limited to the pilot-selected baseline winner and runner-up")

    candidate = get_candidate_by_id(config.candidate_id)
    train_records = load_split_records(config.train_split_path)
    val_records = load_split_records(config.val_split_path)
    # build_training_examples turns raw DatasetRecord dicts (label,
    # risk_tier, text, spans, explanation) into the actual prompt/response
    # pairs the model will be trained on — candidate-specific because
    # different base models can want slightly different prompt formatting
    # conventions.
    train_examples = build_training_examples(train_records, candidate)
    val_examples = build_training_examples(val_records, candidate)

    if config.dry_run:
        # dry_run short-circuits BEFORE touching torch/transformers at
        # all — it only proves the data loading + registry plumbing works,
        # deliberately doesn't import the heavy training stack.
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
    # Merge in everything else the trainer returned (device, quantization_mode,
    # checkpoint_path, metrics, etc.) EXCEPT artifact_path, which was
    # already consumed above to build artifact_record and would be
    # redundant/stale to include again here.
    result.update({key: value for key, value in trainer_result.items() if key != "artifact_path"})
    return result
