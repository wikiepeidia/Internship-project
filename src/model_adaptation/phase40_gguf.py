"""Fail-closed GGUF export for a completed Phase 40 Qwen full run.

This module is deliberately separate from the hash-bound training/operator
implementation.  It treats a completed run bundle as immutable input, reloads
the pinned base model without four-bit quantization, merges the exact selected
PEFT adapter, and converts the temporary merged Hugging Face model to Q8_0.

The exporter never reads a dataset split and never writes into the full-run
bundle or the model registry.
"""

from __future__ import annotations

import argparse
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path, PurePosixPath, PureWindowsPath
import re
import shutil
import stat
import subprocess
import sys
import tempfile
from typing import Any, Protocol

from src.model_adaptation.phase40_evidence import EvidenceStatus, RunEvidence, verify_phase40_bundle
from src.model_adaptation.phase40_modes import ModelFamily, RunKind
from src.model_adaptation.registry import build_model_checksum


SCHEMA_VERSION = "phase40-gguf-export-v1"
QWEN_GGUF_VERIFICATION_RECEIPT_SCHEMA_VERSION = (
    "phase40-qwen-gguf-verification-receipt-v1"
)
QWEN_GGUF_VERIFICATION_RECEIPT_FILENAME = "qwen-gguf-verification-receipt.json"
QWEN_GGUF_VERIFICATION_RECEIPT_RELATIVE_PATH = PurePosixPath(
    "data/models/phase40/qwen-gguf-verification-receipt.json"
)
_PHASE40_RUN_REQUEST_RELATIVE_PATH = PurePosixPath(
    "data/models/phase40/full-run-request.json"
)
_PHASE40_SCOPE_AMENDMENT_RELATIVE_PATH = PurePosixPath(
    "data/models/phase40/two-full-model-scope-amendment.json"
)
OUTTYPE = "q8_0"
CONVERTER_FILENAME = "convert_hf_to_gguf.py"
CONVERTER_PACKAGE_NAME = "gguf"
CONVERTER_PACKAGE_VERSION = "0.19.0"
CONVERTER_SCRIPT_SHA256 = "f227273d926fd8ba1c5215ca9ba64d63e641b3277e6f225080b4aac434999b55"
LLAMA_CPP_PYTHON_VERSION = "0.3.23"
BASE_PROVENANCE_FILENAME = "phase40-base-model-provenance.json"
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_PORTABLE_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,191}$")
_PORTABLE_FILENAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
_PERSONAL_ABSOLUTE_PATH_RE = re.compile(
    r"(?i)(?:^[A-Z]:[\\/]|^\\\\|^/(?:home|Users)/|[A-Z]:[\\/]Users[\\/])"
)
_REDIRECTING_REPARSE_TAGS = frozenset(
    {
        getattr(stat, "IO_REPARSE_TAG_SYMLINK", 0xA000000C),
        getattr(stat, "IO_REPARSE_TAG_MOUNT_POINT", 0xA0000003),
    }
)
_SANITIZED_COMMAND = (
    "python",
    "<PINNED_CONVERTER>",
    "<TEMP_MERGED_HF>",
    "--outfile",
    "<TEMP_Q8_0_GGUF>",
    "--outtype",
    OUTTYPE,
)


class BundleVerifier(Protocol):
    def __call__(self, run_root: Path) -> RunEvidence: ...


class BaseSnapshotVerifier(Protocol):
    def __call__(
        self,
        snapshot_path: Path,
        *,
        expected_model_id: str,
        expected_model_revision: str,
        manifest_path: Path | None,
    ) -> Any: ...


class GGUFExportManifestVerifier(Protocol):
    def __call__(
        self,
        manifest_path: Path,
        *,
        rerun_load_smoke: bool,
    ) -> Mapping[str, Any]: ...


@dataclass(frozen=True, slots=True)
class ModelBackend:
    """Injected model-library boundary; tests do not load a real checkpoint."""

    load_tokenizer: Callable[[Path], Any]
    load_base_model: Callable[[Path], Any]
    attach_adapter: Callable[[Any, Path], Any]


@dataclass(frozen=True, slots=True)
class LoadSmokeResult:
    passed: bool
    loader: str
    loader_version: str
    detail: str


@dataclass(frozen=True, slots=True)
class GGUFExportDependencies:
    """Dependency seams for model, process, clock, and provenance operations."""

    model_backend: ModelBackend
    command_runner: Callable[..., Any]
    smoke_loader: Callable[[Path], LoadSmokeResult]
    bundle_verifier: BundleVerifier
    base_snapshot_verifier: BaseSnapshotVerifier
    selected_adapter_identity_resolver: Callable[[Path], str]
    package_version_resolver: Callable[[str], str]
    authorized_converter_sha256: str
    now: Callable[[], datetime]


@dataclass(frozen=True, slots=True)
class VerifiedSource:
    run_root: Path
    evidence: RunEvidence
    run_root_sha256: str
    run_evidence_sha256: str
    selected_path: Path
    selected_sha256: str
    retained_provenance_sha256: str
    base_model_path: Path
    base_manifest_path: Path
    base_snapshot: Any


@dataclass(frozen=True, slots=True)
class GGUFExportResult:
    output_path: Path
    manifest_path: Path
    output_sha256: str
    manifest: Mapping[str, Any]


@dataclass(frozen=True, slots=True)
class GGUFVerificationContext:
    """Code-fixed Phase 40 identities expected by the portable receipt."""

    request_sha256: str
    scope_amendment_sha256: str
    selected_run_id: str
    selected_checkpoint_identity: str


def _absolute(path: Path) -> Path:
    return Path(os.path.abspath(os.path.normpath(os.fspath(path))))


def _is_within(path: Path, root: Path) -> bool:
    absolute_path = _absolute(path)
    absolute_root = _absolute(root)
    return absolute_path == absolute_root or absolute_root in absolute_path.parents


def _component_chain(path: Path) -> tuple[Path, ...]:
    components: list[Path] = []
    current = _absolute(path)
    while True:
        components.append(current)
        if current.parent == current:
            break
        current = current.parent
    return tuple(reversed(components))


def _reject_redirecting_components(path: Path, *, include_missing_leaf: bool = True) -> None:
    for component in _component_chain(path):
        if not component.exists():
            if include_missing_leaf:
                continue
            raise FileNotFoundError(component)
        metadata = os.lstat(component)
        tag = getattr(metadata, "st_reparse_tag", 0)
        if stat.S_ISLNK(metadata.st_mode) or tag in _REDIRECTING_REPARSE_TAGS:
            raise ValueError(f"path must not traverse a symbolic link or junction: {component}")


def _regular_file(path: Path, *, description: str) -> Path:
    candidate = _absolute(path)
    _reject_redirecting_components(candidate)
    if not candidate.is_file() or candidate.is_symlink() or candidate.stat().st_size < 1:
        raise ValueError(f"{description} must be a non-empty regular file")
    return candidate


def _regular_directory(path: Path, *, description: str) -> Path:
    candidate = _absolute(path)
    _reject_redirecting_components(candidate, include_missing_leaf=False)
    if not candidate.is_dir() or candidate.is_symlink():
        raise ValueError(f"{description} must be an existing non-symlink directory")
    for child in candidate.rglob("*"):
        metadata = os.lstat(child)
        tag = getattr(metadata, "st_reparse_tag", 0)
        if stat.S_ISLNK(metadata.st_mode) or tag in _REDIRECTING_REPARSE_TAGS:
            raise ValueError(f"{description} contains a symbolic link or junction")
    return candidate


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def _tree_sha256(path: Path) -> str:
    """Hash path, size, and content for every regular file in a safe tree."""

    root = _regular_directory(path, description="input tree")
    digest = hashlib.sha256(b"phase40-gguf-input-tree-v1\0")
    files = tuple(sorted(child for child in root.rglob("*") if child.is_file()))
    if not files:
        raise RuntimeError("input tree is empty")
    for child in files:
        relative = child.relative_to(root).as_posix().encode("utf-8")
        size = child.stat().st_size
        digest.update(len(relative).to_bytes(8, "big"))
        digest.update(relative)
        digest.update(size.to_bytes(8, "big"))
        digest.update(bytes.fromhex(_sha256_file(child)))
    return digest.hexdigest()


def _canonical_json_bytes(payload: Mapping[str, Any]) -> bytes:
    return (
        json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        + "\n"
    ).encode("utf-8")


def _load_json_exact(path: Path) -> dict[str, Any]:
    raw = _regular_file(path, description="JSON manifest").read_bytes()

    def reject_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        output: dict[str, Any] = {}
        for key, value in pairs:
            if key in output:
                raise ValueError(f"duplicate JSON key: {key}")
            output[key] = value
        return output

    try:
        payload = json.loads(
            raw.decode("utf-8", errors="strict"),
            object_pairs_hook=reject_duplicates,
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RuntimeError("manifest must be strict UTF-8 JSON") from exc
    if not isinstance(payload, dict):
        raise RuntimeError("manifest must be a JSON object")
    return payload


def _require_exact_keys(payload: Mapping[str, Any], expected: set[str], *, where: str) -> None:
    if set(payload) != expected:
        raise RuntimeError(
            f"{where} keys mismatch; missing={sorted(expected - set(payload))}, "
            f"extra={sorted(set(payload) - expected)}"
        )


def _require_sha256(value: object, *, where: str) -> str:
    if not isinstance(value, str) or not _SHA256_RE.fullmatch(value):
        raise ValueError(f"{where} must be a lowercase SHA-256")
    return value


def _safe_fact(value: object, *, where: str) -> str:
    if not isinstance(value, str) or not value or len(value) > 256:
        raise ValueError(f"{where} must be a non-empty short string")
    if any(ord(character) < 32 for character in value):
        raise ValueError(f"{where} contains control characters")
    return value


def _reject_lexical_traversal(path: Path, *, where: str) -> None:
    text = os.fspath(path)
    if not isinstance(text, str) or not text or "\x00" in text:
        raise ValueError(f"{where} must be a non-empty filesystem path")
    normalized_separators = text.replace("\\", "/")
    if ".." in PurePosixPath(normalized_separators).parts:
        raise ValueError(f"{where} must not contain path traversal")


def _portable_id(value: object, *, where: str) -> str:
    if (
        not isinstance(value, str)
        or not _PORTABLE_ID_RE.fullmatch(value)
        or value in {".", ".."}
    ):
        raise ValueError(f"{where} must be a portable identifier")
    return value


def _portable_filename(value: object, *, where: str) -> str:
    if (
        not isinstance(value, str)
        or not _PORTABLE_FILENAME_RE.fullmatch(value)
        or PurePosixPath(value).name != value
        or PureWindowsPath(value).name != value
        or value in {".", ".."}
    ):
        raise ValueError(f"{where} must be one portable filename")
    return value


def _reject_absolute_path_leakage(value: object, *, where: str) -> None:
    if isinstance(value, Mapping):
        for key, child in value.items():
            _reject_absolute_path_leakage(child, where=f"{where}.{key}")
        return
    if isinstance(value, list):
        for index, child in enumerate(value):
            _reject_absolute_path_leakage(child, where=f"{where}[{index}]")
        return
    if not isinstance(value, str):
        return
    if (
        _PERSONAL_ABSOLUTE_PATH_RE.search(value)
        or PureWindowsPath(value).is_absolute()
        or PurePosixPath(value).is_absolute()
    ):
        raise ValueError(f"{where} leaks an absolute filesystem path")


def _utc_text(value: datetime) -> str:
    if not isinstance(value, datetime):
        raise TypeError("clock must return datetime")
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("clock must return a timezone-aware datetime")
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _parse_utc(value: object, *, where: str) -> datetime:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise RuntimeError(f"{where} must be a UTC timestamp ending in Z")
    try:
        parsed = datetime.fromisoformat(value.removesuffix("Z") + "+00:00")
    except ValueError as exc:
        raise RuntimeError(f"{where} is not a valid timestamp") from exc
    if parsed.tzinfo is None:
        raise RuntimeError(f"{where} must be timezone-aware")
    return parsed


def _parse_canonical_utc(value: object, *, where: str) -> datetime:
    parsed = _parse_utc(value, where=where)
    if _utc_text(parsed) != value:
        raise RuntimeError(f"{where} must use canonical UTC formatting")
    return parsed


def _default_bundle_verifier(run_root: Path) -> RunEvidence:
    return verify_phase40_bundle(run_root)


def _default_base_snapshot_verifier(
    snapshot_path: Path,
    *,
    expected_model_id: str,
    expected_model_revision: str,
    manifest_path: Path | None,
) -> Any:
    from src.model_adaptation.training import validate_qwen_base_model_snapshot

    return validate_qwen_base_model_snapshot(
        snapshot_path,
        expected_model_id=expected_model_id,
        expected_model_revision=expected_model_revision,
        manifest_path=manifest_path,
    )


def _default_selected_adapter_identity_resolver(adapter_path: Path) -> str:
    import importlib

    torch_module = importlib.import_module("torch")
    from src.model_adaptation.training import _adapter_state_identity, _load_saved_adapter_state

    state = _load_saved_adapter_state(adapter_path, torch_module=torch_module)
    return _adapter_state_identity(state, torch_module=torch_module)


def _default_model_backend() -> ModelBackend:
    def load_tokenizer(path: Path) -> Any:
        import importlib

        transformers_module = importlib.import_module("transformers")
        return transformers_module.AutoTokenizer.from_pretrained(
            str(path),
            local_files_only=True,
            trust_remote_code=False,
        )

    def load_base_model(path: Path) -> Any:
        import importlib

        torch_module = importlib.import_module("torch")
        transformers_module = importlib.import_module("transformers")
        return transformers_module.AutoModelForCausalLM.from_pretrained(
            str(path),
            local_files_only=True,
            trust_remote_code=False,
            low_cpu_mem_usage=True,
            torch_dtype=getattr(torch_module, "bfloat16", "auto"),
            device_map={"": "cpu"},
        )

    def attach_adapter(model: Any, adapter_path: Path) -> Any:
        import importlib

        peft_module = importlib.import_module("peft")
        return peft_module.PeftModel.from_pretrained(
            model,
            str(adapter_path),
            is_trainable=False,
        )

    return ModelBackend(
        load_tokenizer=load_tokenizer,
        load_base_model=load_base_model,
        attach_adapter=attach_adapter,
    )


def _default_smoke_loader(path: Path) -> LoadSmokeResult:
    import importlib

    llama_cpp = importlib.import_module("llama_cpp")
    loader_version = str(getattr(llama_cpp, "__version__", "unknown"))
    if loader_version != LLAMA_CPP_PYTHON_VERSION:
        raise RuntimeError(
            "GGUF load smoke requires the exact runtime package "
            f"llama-cpp-python=={LLAMA_CPP_PYTHON_VERSION}"
        )
    model = llama_cpp.Llama(
        model_path=str(path),
        n_ctx=32,
        n_gpu_layers=0,
        verbose=False,
    )
    close = getattr(model, "close", None)
    if callable(close):
        close()
    return LoadSmokeResult(
        passed=True,
        loader="llama_cpp.Llama",
        loader_version=loader_version,
        detail="constructor load completed",
    )


def default_dependencies() -> GGUFExportDependencies:
    return GGUFExportDependencies(
        model_backend=_default_model_backend(),
        command_runner=subprocess.run,
        smoke_loader=_default_smoke_loader,
        bundle_verifier=_default_bundle_verifier,
        base_snapshot_verifier=_default_base_snapshot_verifier,
        selected_adapter_identity_resolver=_default_selected_adapter_identity_resolver,
        package_version_resolver=importlib.metadata.version,
        authorized_converter_sha256=CONVERTER_SCRIPT_SHA256,
        now=lambda: datetime.now(timezone.utc),
    )


def _selected_model_artifact(evidence: RunEvidence) -> Any:
    candidates = [artifact for artifact in evidence.artifacts if artifact.role == "model_artifact"]
    if len(candidates) != 1:
        raise RuntimeError("Phase 40 full run must contain exactly one selected model artifact")
    artifact = candidates[0]
    if artifact.kind != "directory" or artifact.relative_path != "adapter-or-model":
        raise RuntimeError("Phase 40 selected model artifact is not the canonical adapter-or-model tree")
    return artifact


def _validate_selected_adapter_summary(selected_path: Path, evidence: RunEvidence) -> None:
    if evidence.selected_checkpoint is None:
        raise RuntimeError("Phase 40 full run lacks selected-checkpoint evidence")
    if not evidence.selected_checkpoint.artifact_identity.startswith("adapter-state-sha256:"):
        raise RuntimeError("Phase 40 Qwen selection is not an adapter state")
    summary_path = selected_path / "training-summary.json"
    adapter_config_path = selected_path / "adapter_config.json"
    weight_paths = tuple(selected_path.glob("adapter_model.*"))
    if not summary_path.is_file() or not adapter_config_path.is_file() or not weight_paths:
        raise RuntimeError("selected adapter tree lacks summary, config, or adapter weights")
    summary = _load_json_exact(summary_path)
    selected = summary.get("selected_adapter")
    if not isinstance(selected, dict):
        raise RuntimeError("selected adapter summary lacks selected_adapter metadata")
    bindings = {
        "run_id": evidence.run_id,
        "run_kind": RunKind.FULL.value,
        "model_revision": evidence.model_revision,
        "requested_adaptation_mode": evidence.experiment_identity.adaptation_mode.value,
    }
    for field, expected in bindings.items():
        if summary.get(field) != expected:
            raise RuntimeError(f"selected adapter summary {field} does not match run evidence")
    if selected.get("state_identity") != evidence.selected_checkpoint.artifact_identity:
        raise RuntimeError("selected adapter state identity does not match checkpoint selection")


def _portable_base_manifest(snapshot: Any) -> Mapping[str, Any]:
    portable = getattr(snapshot, "portable_manifest", None)
    if not callable(portable):
        raise RuntimeError("base snapshot verifier returned no portable_manifest")
    payload = portable()
    if not isinstance(payload, Mapping):
        raise RuntimeError("base snapshot portable manifest is invalid")
    return payload


def _resolve_verified_source(
    run_root: Path,
    base_model_path: Path,
    base_manifest_path: Path | None,
    *,
    dependencies: GGUFExportDependencies,
) -> VerifiedSource:
    root = _regular_directory(run_root, description="Phase 40 full-run root")
    evidence = dependencies.bundle_verifier(root)
    if (
        evidence.status != EvidenceStatus.COMPLETE
        or evidence.run_kind != RunKind.FULL
        or evidence.experiment_identity.run_kind != RunKind.FULL
    ):
        raise RuntimeError("GGUF export accepts only a verified complete Phase 40 full run")
    if evidence.experiment_identity.model_family != ModelFamily.QWEN:
        raise RuntimeError("GGUF export accepts only a Phase 40 Qwen full run")
    artifact = _selected_model_artifact(evidence)
    selected_path = _regular_directory(
        root / PurePosixPath(artifact.relative_path),
        description="selected adapter-or-model tree",
    )
    selected_sha256 = build_model_checksum(selected_path)
    if selected_sha256 != artifact.sha256:
        raise RuntimeError("selected adapter-or-model tree hash differs from run evidence")
    _validate_selected_adapter_summary(selected_path, evidence)
    actual_adapter_identity = dependencies.selected_adapter_identity_resolver(selected_path)
    if actual_adapter_identity != evidence.selected_checkpoint.artifact_identity:
        raise RuntimeError("selected adapter tensors differ from checkpoint selection evidence")

    base_path = _regular_directory(base_model_path, description="pinned Qwen base-model snapshot")
    manifest_path = (
        base_path / BASE_PROVENANCE_FILENAME
        if base_manifest_path is None
        else _regular_file(base_manifest_path, description="base-model provenance manifest")
    )
    snapshot = dependencies.base_snapshot_verifier(
        base_path,
        expected_model_id=evidence.model_id,
        expected_model_revision=evidence.model_revision,
        manifest_path=manifest_path,
    )
    for field, expected in (
        ("model_id", evidence.model_id),
        ("model_revision", evidence.model_revision),
    ):
        if getattr(snapshot, field, None) != expected:
            raise RuntimeError(f"verified base snapshot {field} differs from run evidence")
    retained_path = _regular_file(
        selected_path / BASE_PROVENANCE_FILENAME,
        description="selected adapter retained base provenance",
    )
    retained_bytes = retained_path.read_bytes()
    if retained_bytes != _canonical_json_bytes(dict(_portable_base_manifest(snapshot))):
        raise RuntimeError("selected adapter retained provenance differs from the pinned base snapshot")

    run_evidence_path = _regular_file(root / "run-evidence.json", description="run evidence")
    return VerifiedSource(
        run_root=root,
        evidence=evidence,
        run_root_sha256=_tree_sha256(root),
        run_evidence_sha256=_sha256_file(run_evidence_path),
        selected_path=selected_path,
        selected_sha256=selected_sha256,
        retained_provenance_sha256=_sha256_file(retained_path),
        base_model_path=base_path,
        base_manifest_path=_regular_file(manifest_path, description="base-model provenance manifest"),
        base_snapshot=snapshot,
    )


def _looks_four_bit(model: Any) -> bool:
    if bool(getattr(model, "is_loaded_in_4bit", False)):
        return True
    config = getattr(model, "config", None)
    if getattr(config, "quantization_config", None) is not None:
        return True
    modules = getattr(model, "modules", None)
    if callable(modules):
        for module in modules():
            module_type = type(module)
            if (
                module_type.__name__ == "Linear4bit"
                and module_type.__module__.startswith("bitsandbytes.")
            ):
                return True
    return False


def _merge_selected_adapter(
    source: VerifiedSource,
    merged_output: Path,
    *,
    backend: ModelBackend,
) -> str:
    tokenizer = backend.load_tokenizer(source.base_model_path)
    base_model = backend.load_base_model(source.base_model_path)
    if _looks_four_bit(base_model):
        raise RuntimeError("GGUF merge requires an ordinary non-4bit base model")
    peft_model = backend.attach_adapter(base_model, source.selected_path)
    if _looks_four_bit(peft_model):
        raise RuntimeError("selected adapter was attached to a four-bit base model")
    merge = getattr(peft_model, "merge_and_unload", None)
    if not callable(merge):
        raise RuntimeError("PEFT merge_and_unload is unavailable; refusing an unmerged GGUF")
    try:
        merged_model = merge(safe_merge=True)
    except TypeError as exc:
        raise RuntimeError("PEFT merge_and_unload does not support the required safe merge") from exc
    if merged_model is None or _looks_four_bit(merged_model):
        raise RuntimeError("PEFT merge did not produce an ordinary non-4bit model")
    merged_output.mkdir(parents=True, exist_ok=False)
    merged_model.save_pretrained(str(merged_output), safe_serialization=True)
    tokenizer.save_pretrained(str(merged_output))
    return _tree_sha256(merged_output)


def _run_converter(
    converter_script: Path,
    expected_converter_sha256: str,
    merged_model_path: Path,
    staged_output_path: Path,
    *,
    command_runner: Callable[..., Any],
    python_executable: Path,
) -> tuple[str, int]:
    script = _regular_file(converter_script, description="llama.cpp converter script")
    if script.name != CONVERTER_FILENAME:
        raise ValueError(f"converter script must be named {CONVERTER_FILENAME}")
    expected = _require_sha256(expected_converter_sha256, where="converter SHA-256")
    before = _sha256_file(script)
    if before != expected:
        raise RuntimeError("llama.cpp converter script SHA-256 does not match its pin")
    command = [
        str(python_executable),
        str(script),
        str(merged_model_path),
        "--outfile",
        str(staged_output_path),
        "--outtype",
        OUTTYPE,
    ]
    completed = command_runner(
        command,
        cwd=str(script.parent),
        check=False,
        capture_output=True,
        text=True,
    )
    returncode = getattr(completed, "returncode", None)
    if not isinstance(returncode, int):
        raise RuntimeError("converter runner returned no integer exit code")
    after = _sha256_file(script)
    if after != expected:
        raise RuntimeError("llama.cpp converter script changed during conversion")
    if returncode != 0:
        raise RuntimeError(f"GGUF converter exited with code {returncode}")
    output = _regular_file(staged_output_path, description="staged GGUF output")
    return _sha256_file(output), returncode


def _smoke_payload(result: LoadSmokeResult) -> dict[str, Any]:
    if not isinstance(result, LoadSmokeResult):
        raise TypeError("smoke loader must return LoadSmokeResult")
    if result.passed is not True:
        raise RuntimeError("GGUF load smoke did not pass")
    return {
        "passed": True,
        "loader": _safe_fact(result.loader, where="smoke loader"),
        "loader_version": _safe_fact(result.loader_version, where="smoke loader version"),
        "detail": _safe_fact(result.detail, where="smoke detail"),
    }


def _source_manifest_payload(source: VerifiedSource) -> dict[str, Any]:
    evidence = source.evidence
    selected = evidence.selected_checkpoint
    assert selected is not None
    snapshot = source.base_snapshot
    return {
        "run_root": str(source.run_root),
        "run_root_sha256": source.run_root_sha256,
        "run_evidence_relative_path": "run-evidence.json",
        "run_evidence_sha256": source.run_evidence_sha256,
        "run_id": evidence.run_id,
        "run_kind": RunKind.FULL.value,
        "model_family": ModelFamily.QWEN.value,
        "adaptation_mode": evidence.experiment_identity.adaptation_mode.value,
        "model_id": evidence.model_id,
        "model_revision": evidence.model_revision,
        "selected_checkpoint": {
            "optimizer_step": selected.optimizer_step,
            "artifact_identity": selected.artifact_identity,
            "safety_gate_passed": selected.safety_gate_passed,
        },
        "selected_model_relative_path": "adapter-or-model",
        "selected_model_sha256": source.selected_sha256,
        "retained_base_provenance_sha256": source.retained_provenance_sha256,
        "base_model_path": str(source.base_model_path),
        "base_manifest_path": str(source.base_manifest_path),
        "base_manifest_sha256": getattr(snapshot, "manifest_sha256"),
        "base_snapshot_content_sha256": getattr(snapshot, "snapshot_content_sha256"),
    }


def _write_new_file(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as handle:
        handle.write(payload)
        handle.flush()
        os.fsync(handle.fileno())


def export_phase40_gguf(
    *,
    run_root: Path,
    base_model_path: Path,
    base_manifest_path: Path | None,
    converter_script: Path,
    converter_sha256: str,
    output_path: Path,
    manifest_path: Path | None = None,
    temp_parent: Path | None = None,
    python_executable: Path | None = None,
    dependencies: GGUFExportDependencies | None = None,
) -> GGUFExportResult:
    """Create and verify one immutable Q8_0 export outside its source run."""

    deps = default_dependencies() if dependencies is None else dependencies
    started_at = _utc_text(deps.now())
    source = _resolve_verified_source(
        run_root,
        base_model_path,
        base_manifest_path,
        dependencies=deps,
    )
    converter = _regular_file(converter_script, description="llama.cpp converter script")
    converter_pin = _require_sha256(converter_sha256, where="converter SHA-256")
    authorized_converter_sha = _require_sha256(
        deps.authorized_converter_sha256,
        where="authorized converter SHA-256",
    )
    if converter_pin != authorized_converter_sha:
        raise RuntimeError("requested converter SHA-256 differs from the fixed tool authority")
    converter_package_version = deps.package_version_resolver(CONVERTER_PACKAGE_NAME)
    if converter_package_version != CONVERTER_PACKAGE_VERSION:
        raise RuntimeError(
            "GGUF conversion requires the exact converter package "
            f"{CONVERTER_PACKAGE_NAME}=={CONVERTER_PACKAGE_VERSION}"
        )
    if _sha256_file(converter) != converter_pin:
        raise RuntimeError("llama.cpp converter script SHA-256 does not match its pin")

    output = _absolute(output_path)
    manifest = _absolute(
        output.with_suffix(output.suffix + ".manifest.json")
        if manifest_path is None
        else manifest_path
    )
    if output.suffix.casefold() != ".gguf":
        raise ValueError("GGUF output path must end in .gguf")
    if output == manifest:
        raise ValueError("GGUF output and manifest paths must differ")
    for candidate, description in ((output, "output"), (manifest, "manifest")):
        if _is_within(candidate, source.run_root):
            raise ValueError(f"GGUF {description} must stay outside the immutable full-run root")
        if _is_within(candidate, source.base_model_path):
            raise ValueError(f"GGUF {description} must stay outside the pinned base snapshot")
        _reject_redirecting_components(candidate.parent)
        if candidate.exists():
            raise FileExistsError(f"refusing to overwrite existing GGUF {description}: {candidate}")

    working_parent = _absolute(output.parent if temp_parent is None else temp_parent)
    if _is_within(working_parent, source.run_root) or _is_within(
        working_parent, source.base_model_path
    ):
        raise ValueError("temporary merge parent must stay outside all immutable input roots")
    working_parent.mkdir(parents=True, exist_ok=True)
    _reject_redirecting_components(working_parent, include_missing_leaf=False)
    output.parent.mkdir(parents=True, exist_ok=True)
    manifest.parent.mkdir(parents=True, exist_ok=True)

    published_output = False
    published_manifest = False
    try:
        with tempfile.TemporaryDirectory(prefix="phase40-gguf-", dir=working_parent) as temporary:
            temporary_root = Path(temporary)
            merged_path = temporary_root / "merged-hf"
            staged_output = temporary_root / "model.q8_0.gguf"
            merged_sha256 = _merge_selected_adapter(
                source,
                merged_path,
                backend=deps.model_backend,
            )
            staged_sha256, returncode = _run_converter(
                converter,
                converter_pin,
                merged_path,
                staged_output,
                command_runner=deps.command_runner,
                python_executable=(
                    _absolute(Path(sys.executable))
                    if python_executable is None
                    else _regular_file(python_executable, description="Python executable")
                ),
            )
            if _tree_sha256(source.run_root) != source.run_root_sha256:
                raise RuntimeError("immutable Phase 40 full-run root changed during GGUF export")
            if build_model_checksum(source.selected_path) != source.selected_sha256:
                raise RuntimeError("selected adapter tree changed during GGUF export")
            if getattr(
                deps.base_snapshot_verifier(
                    source.base_model_path,
                    expected_model_id=source.evidence.model_id,
                    expected_model_revision=source.evidence.model_revision,
                    manifest_path=source.base_manifest_path,
                ),
                "snapshot_content_sha256",
                None,
            ) != getattr(source.base_snapshot, "snapshot_content_sha256"):
                raise RuntimeError("pinned base snapshot changed during GGUF export")

            # Publish without an overwrite window and keep cleanup ownership as
            # soon as the exclusive destination exists.  This remains safe
            # when ``temp_parent`` and the export root are on different file
            # systems, unlike a cross-device ``shutil.move`` interruption.
            with staged_output.open("rb") as source_handle, output.open("xb") as output_handle:
                published_output = True
                shutil.copyfileobj(source_handle, output_handle, length=16 * 1024 * 1024)
                output_handle.flush()
                os.fsync(output_handle.fileno())
            output_sha256 = _sha256_file(_regular_file(output, description="GGUF output"))
            if output_sha256 != staged_sha256:
                raise RuntimeError("GGUF output changed while it was published")
            smoke = _smoke_payload(deps.smoke_loader(output))
            completed_at = _utc_text(deps.now())
            if _parse_utc(completed_at, where="completed_at_utc") < _parse_utc(
                started_at, where="started_at_utc"
            ):
                raise RuntimeError("completion timestamp precedes start timestamp")
            payload: dict[str, Any] = {
                "schema_version": SCHEMA_VERSION,
                "status": "complete",
                "outtype": OUTTYPE,
                "started_at_utc": started_at,
                "completed_at_utc": completed_at,
                "source": _source_manifest_payload(source),
                "merge": {
                    "ordinary_non_4bit_base": True,
                    "merge_and_unload_called": True,
                    "safe_merge": True,
                    "temporary_merged_hf_sha256": merged_sha256,
                    "temporary_merged_hf_retained": False,
                },
                "tool": {
                    "authority_type": "pypi-package-script-hash",
                    "package_name": CONVERTER_PACKAGE_NAME,
                    "package_version": converter_package_version,
                    "converter_path": str(converter),
                    "converter_sha256": converter_pin,
                    "converter_filename": CONVERTER_FILENAME,
                    "sanitized_command": list(_SANITIZED_COMMAND),
                    "returncode": returncode,
                },
                "output": {
                    "path": str(output),
                    "bytes": output.stat().st_size,
                    "sha256": output_sha256,
                },
                "load_smoke": smoke,
                "browser_download": {
                    "path": str(output),
                    "ready": True,
                    "operator_action_required": True,
                    "unattended_browser_download_claimed": False,
                },
                "source_and_registry_mutation": {
                    "full_run_root_mutated": False,
                    "base_snapshot_mutated": False,
                    "registry_mutated": False,
                },
            }
            _write_new_file(manifest, _canonical_json_bytes(payload))
            published_manifest = True

        verified = verify_phase40_gguf_export(
            manifest,
            dependencies=deps,
            rerun_load_smoke=False,
        )
        return GGUFExportResult(
            output_path=output,
            manifest_path=manifest,
            output_sha256=output_sha256,
            manifest=verified,
        )
    except BaseException:
        if published_manifest and manifest.is_file():
            manifest.unlink()
        if published_output and output.is_file():
            output.unlink()
        raise


_TOP_LEVEL_KEYS = {
    "schema_version",
    "status",
    "outtype",
    "started_at_utc",
    "completed_at_utc",
    "source",
    "merge",
    "tool",
    "output",
    "load_smoke",
    "browser_download",
    "source_and_registry_mutation",
}
_SOURCE_KEYS = {
    "run_root",
    "run_root_sha256",
    "run_evidence_relative_path",
    "run_evidence_sha256",
    "run_id",
    "run_kind",
    "model_family",
    "adaptation_mode",
    "model_id",
    "model_revision",
    "selected_checkpoint",
    "selected_model_relative_path",
    "selected_model_sha256",
    "retained_base_provenance_sha256",
    "base_model_path",
    "base_manifest_path",
    "base_manifest_sha256",
    "base_snapshot_content_sha256",
}


def verify_phase40_gguf_export(
    manifest_path: Path,
    *,
    dependencies: GGUFExportDependencies | None = None,
    rerun_load_smoke: bool = True,
) -> dict[str, Any]:
    """Rehash all retained inputs/tool/output and optionally repeat the load smoke."""

    if not isinstance(rerun_load_smoke, bool):
        raise TypeError("rerun_load_smoke must be a boolean")
    deps = default_dependencies() if dependencies is None else dependencies
    path = _regular_file(manifest_path, description="GGUF export manifest")
    payload = _load_json_exact(path)
    _require_exact_keys(payload, _TOP_LEVEL_KEYS, where="GGUF export manifest")
    if payload["schema_version"] != SCHEMA_VERSION or payload["status"] != "complete":
        raise RuntimeError("GGUF export manifest is not a complete supported export")
    if payload["outtype"] != OUTTYPE:
        raise RuntimeError("GGUF export is not the locked q8_0 outtype")
    started = _parse_utc(payload["started_at_utc"], where="started_at_utc")
    completed = _parse_utc(payload["completed_at_utc"], where="completed_at_utc")
    if completed < started:
        raise RuntimeError("completion timestamp precedes start timestamp")

    source_payload = payload["source"]
    if not isinstance(source_payload, dict):
        raise RuntimeError("source must be a JSON object")
    _require_exact_keys(source_payload, _SOURCE_KEYS, where="source")
    for field in (
        "run_root_sha256",
        "run_evidence_sha256",
        "selected_model_sha256",
        "retained_base_provenance_sha256",
        "base_manifest_sha256",
        "base_snapshot_content_sha256",
    ):
        _require_sha256(source_payload[field], where=f"source.{field}")
    if source_payload["run_evidence_relative_path"] != "run-evidence.json":
        raise RuntimeError("source run evidence path is not canonical")
    if source_payload["selected_model_relative_path"] != "adapter-or-model":
        raise RuntimeError("source selected model path is not canonical")

    source = _resolve_verified_source(
        Path(source_payload["run_root"]),
        Path(source_payload["base_model_path"]),
        Path(source_payload["base_manifest_path"]),
        dependencies=deps,
    )
    expected_source = _source_manifest_payload(source)
    if source_payload != expected_source:
        raise RuntimeError("GGUF manifest source identities differ from verified Phase 40 inputs")
    if _is_within(path, source.run_root) or _is_within(path, source.base_model_path):
        raise RuntimeError("GGUF manifest was written inside an immutable input root")

    merge = payload["merge"]
    if not isinstance(merge, dict):
        raise RuntimeError("merge must be a JSON object")
    _require_exact_keys(
        merge,
        {
            "ordinary_non_4bit_base",
            "merge_and_unload_called",
            "safe_merge",
            "temporary_merged_hf_sha256",
            "temporary_merged_hf_retained",
        },
        where="merge",
    )
    if (
        merge["ordinary_non_4bit_base"] is not True
        or merge["merge_and_unload_called"] is not True
        or merge["safe_merge"] is not True
        or merge["temporary_merged_hf_retained"] is not False
    ):
        raise RuntimeError("GGUF merge contract is incomplete")
    _require_sha256(merge["temporary_merged_hf_sha256"], where="merged HF SHA-256")

    tool = payload["tool"]
    if not isinstance(tool, dict):
        raise RuntimeError("tool must be a JSON object")
    _require_exact_keys(
        tool,
        {
            "authority_type",
            "package_name",
            "package_version",
            "converter_path",
            "converter_sha256",
            "converter_filename",
            "sanitized_command",
            "returncode",
        },
        where="tool",
    )
    if tool["authority_type"] != "pypi-package-script-hash":
        raise RuntimeError("GGUF converter has an unsupported authority type")
    if (
        tool["package_name"] != CONVERTER_PACKAGE_NAME
        or tool["package_version"] != CONVERTER_PACKAGE_VERSION
        or deps.package_version_resolver(CONVERTER_PACKAGE_NAME) != CONVERTER_PACKAGE_VERSION
    ):
        raise RuntimeError("GGUF converter package authority changed")
    if tool["converter_filename"] != CONVERTER_FILENAME or tool["returncode"] != 0:
        raise RuntimeError("GGUF converter identity or return code is invalid")
    if tool["sanitized_command"] != list(_SANITIZED_COMMAND):
        raise RuntimeError("GGUF converter command is not the locked sanitized command")
    converter = _regular_file(Path(tool["converter_path"]), description="llama.cpp converter script")
    converter_sha = _require_sha256(tool["converter_sha256"], where="converter SHA-256")
    if converter_sha != _require_sha256(
        deps.authorized_converter_sha256,
        where="authorized converter SHA-256",
    ):
        raise RuntimeError("manifest converter SHA-256 differs from the fixed tool authority")
    if converter.name != CONVERTER_FILENAME or _sha256_file(converter) != converter_sha:
        raise RuntimeError("pinned llama.cpp converter tool changed")

    output_payload = payload["output"]
    if not isinstance(output_payload, dict):
        raise RuntimeError("output must be a JSON object")
    _require_exact_keys(output_payload, {"path", "bytes", "sha256"}, where="output")
    output = _regular_file(Path(output_payload["path"]), description="GGUF output")
    if output.suffix.casefold() != ".gguf":
        raise RuntimeError("verified output path does not end in .gguf")
    if _is_within(output, source.run_root) or _is_within(output, source.base_model_path):
        raise RuntimeError("GGUF output was written inside an immutable input root")
    if (
        isinstance(output_payload["bytes"], bool)
        or not isinstance(output_payload["bytes"], int)
        or output_payload["bytes"] < 1
        or output.stat().st_size != output_payload["bytes"]
    ):
        raise RuntimeError("GGUF output byte count differs from the manifest")
    output_sha = _require_sha256(output_payload["sha256"], where="output SHA-256")
    if _sha256_file(output) != output_sha:
        raise RuntimeError("GGUF output SHA-256 differs from the manifest")

    smoke = payload["load_smoke"]
    if not isinstance(smoke, dict):
        raise RuntimeError("load_smoke must be a JSON object")
    _require_exact_keys(smoke, {"passed", "loader", "loader_version", "detail"}, where="load_smoke")
    if smoke["passed"] is not True:
        raise RuntimeError("GGUF export has no passing load smoke")
    for field in ("loader", "loader_version", "detail"):
        _safe_fact(smoke[field], where=f"load_smoke.{field}")
    if rerun_load_smoke:
        _smoke_payload(deps.smoke_loader(output))

    browser = payload["browser_download"]
    if not isinstance(browser, dict):
        raise RuntimeError("browser_download must be a JSON object")
    _require_exact_keys(
        browser,
        {
            "path",
            "ready",
            "operator_action_required",
            "unattended_browser_download_claimed",
        },
        where="browser_download",
    )
    if browser != {
        "path": str(output),
        "ready": True,
        "operator_action_required": True,
        "unattended_browser_download_claimed": False,
    }:
        raise RuntimeError("browser-download metadata overclaims or identifies the wrong output")

    mutation = payload["source_and_registry_mutation"]
    if not isinstance(mutation, dict):
        raise RuntimeError("source_and_registry_mutation must be a JSON object")
    _require_exact_keys(
        mutation,
        {"full_run_root_mutated", "base_snapshot_mutated", "registry_mutated"},
        where="source_and_registry_mutation",
    )
    if mutation != {
        "full_run_root_mutated": False,
        "base_snapshot_mutated": False,
        "registry_mutated": False,
    }:
        raise RuntimeError("GGUF export manifest claims an input or registry mutation")
    return payload


_GGUF_RECEIPT_TOP_LEVEL_KEYS = {
    "schema_version",
    "status",
    "verified_at_utc",
    "upstream",
    "selection",
    "export",
    "converter",
    "load_smoke",
    "receipt_sha256",
}
_GGUF_RECEIPT_UPSTREAM_KEYS = {
    "request_sha256",
    "scope_amendment_sha256",
}
_GGUF_RECEIPT_SELECTION_KEYS = {
    "model_family",
    "run_kind",
    "adaptation_mode",
    "model_id",
    "model_revision",
    "run_id",
    "selected_checkpoint",
}
_GGUF_RECEIPT_CHECKPOINT_KEYS = {
    "optimizer_step",
    "artifact_identity",
    "safety_gate_passed",
}
_GGUF_RECEIPT_EXPORT_KEYS = {
    "manifest_filename",
    "manifest_sha256",
    "manifest_schema_version",
    "manifest_status",
    "outtype",
    "gguf_filename",
    "gguf_bytes",
    "gguf_sha256",
}
_GGUF_RECEIPT_CONVERTER_KEYS = {
    "authority_type",
    "package_name",
    "package_version",
    "script_filename",
    "script_sha256",
}
_GGUF_RECEIPT_SMOKE_KEYS = {"original_export", "independent_rerun"}
_GGUF_RECEIPT_ORIGINAL_SMOKE_KEYS = {
    "passed",
    "loader",
    "loader_version",
    "detail_sha256",
    "record_sha256",
}
_GGUF_RECEIPT_RERUN_SMOKE_KEYS = {
    "passed",
    "verifier",
    "rerun_load_smoke",
    "manifest_sha256",
}


def _validated_gguf_verification_context(
    context: GGUFVerificationContext,
) -> dict[str, Any]:
    if not isinstance(context, GGUFVerificationContext):
        raise TypeError("context must be GGUFVerificationContext")
    upstream = {
        "request_sha256": _require_sha256(
            context.request_sha256,
            where="request SHA-256",
        ),
        "scope_amendment_sha256": _require_sha256(
            context.scope_amendment_sha256,
            where="scope amendment SHA-256",
        ),
    }
    _portable_id(context.selected_run_id, where="selected Qwen run ID")
    _portable_id(
        context.selected_checkpoint_identity,
        where="selected Qwen checkpoint identity",
    )
    return upstream


def _strict_verified_export_manifest(
    manifest_path: Path,
    *,
    manifest_verifier: GGUFExportManifestVerifier | None,
) -> tuple[Path, bytes, dict[str, Any]]:
    requested_path = Path(manifest_path)
    _reject_lexical_traversal(requested_path, where="GGUF export manifest path")
    if not requested_path.is_absolute():
        raise ValueError("GGUF export manifest path must be absolute")
    path = _regular_file(requested_path, description="GGUF export manifest")
    manifest_filename = _portable_filename(path.name, where="GGUF export manifest filename")
    if not manifest_filename.endswith(".gguf.manifest.json"):
        raise ValueError("GGUF export manifest filename is not canonical")
    before = path.read_bytes()
    verifier = verify_phase40_gguf_export if manifest_verifier is None else manifest_verifier
    verified = verifier(path, rerun_load_smoke=True)
    if not isinstance(verified, Mapping):
        raise TypeError("GGUF export manifest verifier must return a mapping")
    after = _regular_file(path, description="GGUF export manifest").read_bytes()
    if after != before:
        raise RuntimeError("GGUF export manifest changed during independent verification")
    payload = _load_json_exact(path)
    if after != _canonical_json_bytes(payload):
        raise RuntimeError("GGUF export manifest is not canonical JSON")
    if dict(verified) != payload:
        raise RuntimeError("GGUF export verifier result differs from the manifest bytes")
    return path, after, payload


def _require_absolute_manifest_path(value: object, *, where: str) -> Path:
    if not isinstance(value, str):
        raise ValueError(f"{where} must be an absolute path string")
    lexical = Path(value)
    _reject_lexical_traversal(lexical, where=where)
    if not lexical.is_absolute():
        raise ValueError(f"{where} must be absolute")
    return lexical


def _build_qwen_gguf_receipt_core(
    *,
    manifest_path: Path,
    manifest_bytes: bytes,
    manifest: Mapping[str, Any],
    context: GGUFVerificationContext,
    verified_at_utc: str,
) -> dict[str, Any]:
    upstream = _validated_gguf_verification_context(context)
    verified_at = _parse_canonical_utc(verified_at_utc, where="verified_at_utc")
    _require_exact_keys(manifest, _TOP_LEVEL_KEYS, where="GGUF export manifest")
    if (
        manifest.get("schema_version") != SCHEMA_VERSION
        or manifest.get("status") != "complete"
        or manifest.get("outtype") != OUTTYPE
    ):
        raise RuntimeError("GGUF export manifest is not a complete locked Q8_0 export")
    started = _parse_canonical_utc(manifest.get("started_at_utc"), where="started_at_utc")
    completed = _parse_canonical_utc(
        manifest.get("completed_at_utc"),
        where="completed_at_utc",
    )
    if completed < started or verified_at < completed:
        raise RuntimeError("GGUF receipt chronology is invalid")

    source = manifest.get("source")
    if not isinstance(source, Mapping):
        raise RuntimeError("GGUF export source must be an object")
    _require_exact_keys(source, _SOURCE_KEYS, where="GGUF export source")
    for field in ("run_root", "base_model_path", "base_manifest_path"):
        _require_absolute_manifest_path(source.get(field), where=f"source.{field}")
    if (
        source.get("model_family") != ModelFamily.QWEN.value
        or source.get("run_kind") != RunKind.FULL.value
        or source.get("adaptation_mode") != "qlora"
        or source.get("run_id") != context.selected_run_id
    ):
        raise RuntimeError("GGUF export is not the context-selected full Qwen QLoRA run")
    checkpoint = source.get("selected_checkpoint")
    if not isinstance(checkpoint, Mapping):
        raise RuntimeError("GGUF export selected checkpoint must be an object")
    _require_exact_keys(checkpoint, _GGUF_RECEIPT_CHECKPOINT_KEYS, where="selected checkpoint")
    optimizer_step = checkpoint.get("optimizer_step")
    if (
        isinstance(optimizer_step, bool)
        or not isinstance(optimizer_step, int)
        or optimizer_step < 1
        or checkpoint.get("artifact_identity") != context.selected_checkpoint_identity
        or checkpoint.get("safety_gate_passed") is not True
    ):
        raise RuntimeError("GGUF export selected checkpoint differs from the approved selection")
    model_id = _safe_fact(source.get("model_id"), where="source.model_id")
    model_revision = _portable_id(source.get("model_revision"), where="source.model_revision")

    output = manifest.get("output")
    if not isinstance(output, Mapping):
        raise RuntimeError("GGUF export output must be an object")
    _require_exact_keys(output, {"path", "bytes", "sha256"}, where="GGUF export output")
    output_path = _require_absolute_manifest_path(output.get("path"), where="output.path")
    output_filename = _portable_filename(output_path.name, where="GGUF output filename")
    if not output_filename.endswith(".gguf"):
        raise RuntimeError("GGUF output filename must end in .gguf")
    output_bytes = output.get("bytes")
    if isinstance(output_bytes, bool) or not isinstance(output_bytes, int) or output_bytes < 1:
        raise RuntimeError("GGUF output byte count is invalid")
    output_sha256 = _require_sha256(output.get("sha256"), where="GGUF output SHA-256")

    tool = manifest.get("tool")
    if not isinstance(tool, Mapping):
        raise RuntimeError("GGUF converter authority must be an object")
    _require_absolute_manifest_path(tool.get("converter_path"), where="tool.converter_path")
    if (
        tool.get("authority_type") != "pypi-package-script-hash"
        or tool.get("package_name") != CONVERTER_PACKAGE_NAME
        or tool.get("package_version") != CONVERTER_PACKAGE_VERSION
        or tool.get("converter_filename") != CONVERTER_FILENAME
    ):
        raise RuntimeError("GGUF converter authority differs from the locked converter")
    converter_sha256 = _require_sha256(
        tool.get("converter_sha256"),
        where="converter script SHA-256",
    )

    smoke = manifest.get("load_smoke")
    if not isinstance(smoke, Mapping):
        raise RuntimeError("GGUF original load smoke must be an object")
    _require_exact_keys(
        smoke,
        {"passed", "loader", "loader_version", "detail"},
        where="GGUF original load smoke",
    )
    if smoke.get("passed") is not True:
        raise RuntimeError("GGUF original export load smoke did not pass")
    loader = _safe_fact(smoke.get("loader"), where="load_smoke.loader")
    loader_version = _safe_fact(
        smoke.get("loader_version"),
        where="load_smoke.loader_version",
    )
    detail = _safe_fact(smoke.get("detail"), where="load_smoke.detail")
    manifest_sha256 = hashlib.sha256(manifest_bytes).hexdigest()
    core: dict[str, Any] = {
        "schema_version": QWEN_GGUF_VERIFICATION_RECEIPT_SCHEMA_VERSION,
        "status": "verified",
        "verified_at_utc": verified_at_utc,
        "upstream": upstream,
        "selection": {
            "model_family": ModelFamily.QWEN.value,
            "run_kind": RunKind.FULL.value,
            "adaptation_mode": "qlora",
            "model_id": model_id,
            "model_revision": model_revision,
            "run_id": context.selected_run_id,
            "selected_checkpoint": {
                "optimizer_step": optimizer_step,
                "artifact_identity": context.selected_checkpoint_identity,
                "safety_gate_passed": True,
            },
        },
        "export": {
            "manifest_filename": _portable_filename(
                manifest_path.name,
                where="GGUF export manifest filename",
            ),
            "manifest_sha256": manifest_sha256,
            "manifest_schema_version": SCHEMA_VERSION,
            "manifest_status": "complete",
            "outtype": OUTTYPE,
            "gguf_filename": output_filename,
            "gguf_bytes": output_bytes,
            "gguf_sha256": output_sha256,
        },
        "converter": {
            "authority_type": "pypi-package-script-hash",
            "package_name": CONVERTER_PACKAGE_NAME,
            "package_version": CONVERTER_PACKAGE_VERSION,
            "script_filename": CONVERTER_FILENAME,
            "script_sha256": converter_sha256,
        },
        "load_smoke": {
            "original_export": {
                "passed": True,
                "loader": loader,
                "loader_version": loader_version,
                "detail_sha256": hashlib.sha256(detail.encode("utf-8")).hexdigest(),
                "record_sha256": hashlib.sha256(
                    _canonical_json_bytes(dict(smoke))
                ).hexdigest(),
            },
            "independent_rerun": {
                "passed": True,
                "verifier": "verify_phase40_gguf_export",
                "rerun_load_smoke": True,
                "manifest_sha256": manifest_sha256,
            },
        },
    }
    _reject_absolute_path_leakage(core, where="GGUF verification receipt")
    return core


def _validate_qwen_gguf_receipt_shape(payload: Mapping[str, Any]) -> None:
    _require_exact_keys(payload, _GGUF_RECEIPT_TOP_LEVEL_KEYS, where="GGUF receipt")
    nested_contracts = (
        ("upstream", _GGUF_RECEIPT_UPSTREAM_KEYS),
        ("selection", _GGUF_RECEIPT_SELECTION_KEYS),
        ("export", _GGUF_RECEIPT_EXPORT_KEYS),
        ("converter", _GGUF_RECEIPT_CONVERTER_KEYS),
        ("load_smoke", _GGUF_RECEIPT_SMOKE_KEYS),
    )
    for field, keys in nested_contracts:
        child = payload.get(field)
        if not isinstance(child, Mapping):
            raise RuntimeError(f"GGUF receipt {field} must be an object")
        _require_exact_keys(child, keys, where=f"GGUF receipt {field}")
    selection = payload["selection"]
    checkpoint = selection.get("selected_checkpoint")
    if not isinstance(checkpoint, Mapping):
        raise RuntimeError("GGUF receipt selected checkpoint must be an object")
    _require_exact_keys(checkpoint, _GGUF_RECEIPT_CHECKPOINT_KEYS, where="GGUF receipt checkpoint")
    load_smoke = payload["load_smoke"]
    original = load_smoke.get("original_export")
    rerun = load_smoke.get("independent_rerun")
    if not isinstance(original, Mapping) or not isinstance(rerun, Mapping):
        raise RuntimeError("GGUF receipt smoke records must be objects")
    _require_exact_keys(
        original,
        _GGUF_RECEIPT_ORIGINAL_SMOKE_KEYS,
        where="GGUF receipt original smoke",
    )
    _require_exact_keys(
        rerun,
        _GGUF_RECEIPT_RERUN_SMOKE_KEYS,
        where="GGUF receipt rerun smoke",
    )


def _verified_repository_root(repo_root: Path) -> Path:
    requested_root = Path(repo_root)
    _reject_lexical_traversal(requested_root, where="repository root")
    if not requested_root.is_absolute():
        raise ValueError("repository root must be absolute")
    root = _absolute(requested_root)
    _reject_redirecting_components(root, include_missing_leaf=False)
    if not root.is_dir() or root.is_symlink():
        raise ValueError("repository root must be an existing non-symlink directory")
    return root


def _verify_gguf_receipt_upstream_authorities(
    repo_root: Path,
    context: GGUFVerificationContext,
) -> None:
    root = _verified_repository_root(repo_root)
    expected = (
        (
            _PHASE40_RUN_REQUEST_RELATIVE_PATH,
            context.request_sha256,
            "run request",
        ),
        (
            _PHASE40_SCOPE_AMENDMENT_RELATIVE_PATH,
            context.scope_amendment_sha256,
            "scope amendment",
        ),
    )
    for relative_path, expected_sha256, description in expected:
        path = _absolute(root / relative_path)
        if not _is_within(path, root):
            raise RuntimeError(f"canonical Phase 40 {description} escaped the repository root")
        authority = _regular_file(path, description=f"canonical Phase 40 {description}")
        raw = authority.read_bytes()
        payload = _load_json_exact(authority)
        if raw != _canonical_json_bytes(payload):
            raise RuntimeError(f"canonical Phase 40 {description} is not canonical JSON")
        if hashlib.sha256(raw).hexdigest() != expected_sha256:
            raise RuntimeError(
                f"GGUF verification context is stale for canonical Phase 40 {description}"
            )


def _canonical_qwen_gguf_receipt_path(repo_root: Path, *, must_exist: bool) -> Path:
    root = _verified_repository_root(repo_root)
    canonical = _absolute(root / QWEN_GGUF_VERIFICATION_RECEIPT_RELATIVE_PATH)
    if not _is_within(canonical, root):
        raise RuntimeError("canonical GGUF verification receipt escaped the repository root")
    if must_exist:
        return _regular_file(canonical, description="GGUF verification receipt")
    _reject_redirecting_components(canonical.parent)
    if canonical.exists():
        raise FileExistsError(f"refusing to overwrite GGUF verification receipt: {canonical}")
    return canonical


def freeze_phase40_qwen_gguf_verification_receipt(
    *,
    repo_root: Path,
    export_manifest_path: Path,
    context: GGUFVerificationContext,
    manifest_verifier: GGUFExportManifestVerifier | None = None,
    now: Callable[[], datetime] | None = None,
) -> dict[str, Any]:
    """Freeze the portable selected-Qwen Q8_0 authority after a fresh load smoke."""

    _validated_gguf_verification_context(context)
    _verify_gguf_receipt_upstream_authorities(repo_root, context)
    destination = _canonical_qwen_gguf_receipt_path(repo_root, must_exist=False)
    manifest_path, manifest_bytes, manifest = _strict_verified_export_manifest(
        export_manifest_path,
        manifest_verifier=manifest_verifier,
    )
    clock = (lambda: datetime.now(timezone.utc)) if now is None else now
    core = _build_qwen_gguf_receipt_core(
        manifest_path=manifest_path,
        manifest_bytes=manifest_bytes,
        manifest=manifest,
        context=context,
        verified_at_utc=_utc_text(clock()),
    )
    payload = {
        **core,
        "receipt_sha256": hashlib.sha256(_canonical_json_bytes(core)).hexdigest(),
    }
    _validate_qwen_gguf_receipt_shape(payload)
    _reject_absolute_path_leakage(payload, where="GGUF verification receipt")
    _write_new_file(destination, _canonical_json_bytes(payload))
    return payload


def verify_phase40_qwen_gguf_verification_receipt(
    *,
    repo_root: Path,
    export_manifest_path: Path,
    context: GGUFVerificationContext,
    manifest_verifier: GGUFExportManifestVerifier | None = None,
) -> dict[str, Any]:
    """Reverify a portable selected-Qwen receipt against current canonical inputs."""

    upstream = _validated_gguf_verification_context(context)
    _verify_gguf_receipt_upstream_authorities(repo_root, context)
    path = _canonical_qwen_gguf_receipt_path(repo_root, must_exist=True)
    raw = path.read_bytes()
    payload = _load_json_exact(path)
    if raw != _canonical_json_bytes(payload):
        raise RuntimeError("GGUF verification receipt is not canonical JSON")
    _validate_qwen_gguf_receipt_shape(payload)
    if (
        payload.get("schema_version") != QWEN_GGUF_VERIFICATION_RECEIPT_SCHEMA_VERSION
        or payload.get("status") != "verified"
    ):
        raise RuntimeError("GGUF verification receipt is not a supported verified receipt")
    stored_self_hash = _require_sha256(
        payload.get("receipt_sha256"),
        where="GGUF verification receipt self-hash",
    )
    core = {key: value for key, value in payload.items() if key != "receipt_sha256"}
    if hashlib.sha256(_canonical_json_bytes(core)).hexdigest() != stored_self_hash:
        raise RuntimeError("GGUF verification receipt self-hash mismatch")
    if payload.get("upstream") != upstream:
        raise RuntimeError("GGUF verification receipt is stale for the expected upstream authority")
    selection = payload["selection"]
    checkpoint = selection["selected_checkpoint"]
    if (
        selection.get("run_id") != context.selected_run_id
        or checkpoint.get("artifact_identity") != context.selected_checkpoint_identity
    ):
        raise RuntimeError("GGUF verification receipt is stale for the selected Qwen checkpoint")
    _reject_absolute_path_leakage(payload, where="GGUF verification receipt")

    manifest_path, manifest_bytes, manifest = _strict_verified_export_manifest(
        export_manifest_path,
        manifest_verifier=manifest_verifier,
    )
    current_manifest_sha256 = hashlib.sha256(manifest_bytes).hexdigest()
    if payload["export"].get("manifest_sha256") != current_manifest_sha256:
        raise RuntimeError("GGUF verification receipt is stale for the export manifest")
    expected_core = _build_qwen_gguf_receipt_core(
        manifest_path=manifest_path,
        manifest_bytes=manifest_bytes,
        manifest=manifest,
        context=context,
        verified_at_utc=payload["verified_at_utc"],
    )
    if core != expected_core:
        raise RuntimeError("GGUF verification receipt differs from current verified evidence")
    return payload


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m src.model_adaptation.phase40_gguf",
        description="Export or verify an immutable Phase 40 Qwen full run as Q8_0 GGUF.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    export_parser = subparsers.add_parser("export", help="merge, convert, smoke, and verify")
    export_parser.add_argument("--run-root", type=Path, required=True)
    export_parser.add_argument("--base-model-path", type=Path, required=True)
    export_parser.add_argument("--base-manifest-path", type=Path)
    export_parser.add_argument("--converter-script", type=Path, required=True)
    export_parser.add_argument("--converter-sha256", required=True)
    export_parser.add_argument("--output-path", type=Path, required=True)
    export_parser.add_argument("--manifest-path", type=Path)
    export_parser.add_argument("--temp-parent", type=Path)
    export_parser.add_argument("--python-executable", type=Path)
    verify_parser = subparsers.add_parser("verify", help="rehash and repeat the GGUF load smoke")
    verify_parser.add_argument("--manifest-path", type=Path, required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    arguments = _build_parser().parse_args(argv)
    if arguments.command == "export":
        result = export_phase40_gguf(
            run_root=arguments.run_root,
            base_model_path=arguments.base_model_path,
            base_manifest_path=arguments.base_manifest_path,
            converter_script=arguments.converter_script,
            converter_sha256=arguments.converter_sha256,
            output_path=arguments.output_path,
            manifest_path=arguments.manifest_path,
            temp_parent=arguments.temp_parent,
            python_executable=arguments.python_executable,
        )
        print(
            json.dumps(
                {
                    "status": "complete",
                    "output_path": str(result.output_path),
                    "manifest_path": str(result.manifest_path),
                    "output_sha256": result.output_sha256,
                    "browser_download_requires_operator_action": True,
                },
                ensure_ascii=False,
                sort_keys=True,
            )
        )
        return 0
    verified = verify_phase40_gguf_export(arguments.manifest_path)
    print(
        json.dumps(
            {
                "status": "verified",
                "output_path": verified["output"]["path"],
                "output_sha256": verified["output"]["sha256"],
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [
    "GGUFExportDependencies",
    "GGUFExportManifestVerifier",
    "GGUFExportResult",
    "GGUFVerificationContext",
    "LoadSmokeResult",
    "ModelBackend",
    "QWEN_GGUF_VERIFICATION_RECEIPT_FILENAME",
    "QWEN_GGUF_VERIFICATION_RECEIPT_RELATIVE_PATH",
    "QWEN_GGUF_VERIFICATION_RECEIPT_SCHEMA_VERSION",
    "default_dependencies",
    "export_phase40_gguf",
    "freeze_phase40_qwen_gguf_verification_receipt",
    "main",
    "verify_phase40_gguf_export",
    "verify_phase40_qwen_gguf_verification_receipt",
]
