"""Archive-closed operator CLI for Phase 40 external runs.

This module intentionally imports only the Python standard library at import
time.  Each command loads the smallest Phase 40 implementation slice it needs
after argparse has accepted an explicit positive operation.  In particular,
``--help``, request checks, notebook checks, and doctor checks cannot import a
training backend or start model acquisition.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib
import importlib.metadata
import importlib.util
import json
import os
from pathlib import Path
import re
import sys
from types import ModuleType
from typing import Any, Sequence


_REQUEST_RELATIVE_PATH = Path("data/models/phase40/full-run-request.json")
_CHECKPOINT_PATTERN = re.compile(r"checkpoint-([0-9]+)")
_BASE_MODEL_RELATIVE_PATHS = {
    "qwen": Path("data/models/phase40/base/qwen3-4b-instruct-2507"),
    "phobert": Path("data/models/phase40/base/phobert-base-v2"),
}
_BASE_MODEL_MANIFEST_RELATIVE_PATHS = {
    "qwen": Path("data/models/phase40/base/qwen3-4b-instruct-2507.provenance.json"),
    "phobert": Path("data/models/phase40/base/phobert-base-v2.provenance.json"),
}
_QWEN_DEPENDENCIES = {
    "accelerate": "1.13.0",
    "huggingface-hub": "1.16.1",
    "peft": "0.19.1",
    "pydantic": "2.13.4",
    "pydantic-settings": "2.14.1",
    "scikit-learn": "1.8.0",
    "torch": "2.12.0+cu132",
    "transformers": "5.9.0",
}
_PHOBERT_DEPENDENCIES = {
    "accelerate": "1.13.0",
    "huggingface-hub": "1.16.1",
    "pydantic": "2.13.4",
    "pydantic-settings": "2.14.1",
    "scikit-learn": "1.8.0",
    "torch": "2.12.0+cu132",
    "transformers": "5.9.0",
    "underthesea": "9.5.0",
}


class _DuplicateJsonKey(ValueError):
    pass


def _reject_duplicate_json_keys(pairs: list[tuple[str, object]]) -> dict[str, object]:
    value: dict[str, object] = {}
    for key, item in pairs:
        if key in value:
            raise _DuplicateJsonKey(f"duplicate JSON key: {key}")
        value[key] = item
    return value


def _read_json_object(path: Path) -> dict[str, object]:
    path = Path(path)
    if not path.is_file() or path.is_symlink():
        raise FileNotFoundError(f"missing safe JSON file: {path}")
    try:
        value = json.loads(
            path.read_text(encoding="utf-8", errors="strict"),
            object_pairs_hook=_reject_duplicate_json_keys,
        )
    except (UnicodeDecodeError, json.JSONDecodeError, _DuplicateJsonKey) as exc:
        raise ValueError(f"invalid strict JSON: {path}") from exc
    if not isinstance(value, dict):
        raise ValueError(f"JSON root must be an object: {path}")
    return value


def _import_module(name: str) -> ModuleType:
    """One monkeypatchable lazy-import seam used by fake-only tests."""

    return importlib.import_module(name)


def _lexical_absolute(path: Path) -> Path:
    return Path(os.path.abspath(os.path.normpath(os.fspath(path))))


def _same_path(left: Path, right: Path) -> bool:
    return os.path.normcase(os.fspath(_lexical_absolute(left))) == os.path.normcase(
        os.fspath(_lexical_absolute(right))
    )


def _repo_root_for_request(request_path: Path, supplied_root: Path | None) -> Path:
    request_path = _lexical_absolute(request_path)
    if supplied_root is None:
        root = request_path
        for _ in _REQUEST_RELATIVE_PATH.parts:
            root = root.parent
    else:
        root = _lexical_absolute(supplied_root)
    expected = root / _REQUEST_RELATIVE_PATH
    if not _same_path(request_path, expected):
        raise ValueError(
            "run request must be the canonical repository-relative "
            f"{_REQUEST_RELATIVE_PATH.as_posix()}"
        )
    return root


def _load_verified_request(
    request_path: Path,
    *,
    repo_root: Path | None,
    verify_input: bool,
) -> tuple[Any, Path]:
    handoff = _import_module("src.model_adaptation.phase40_handoff")
    root = _repo_root_for_request(Path(request_path), repo_root)
    request = handoff.RunRequest.model_validate(_read_json_object(Path(request_path)))
    handoff.verify_phase40_run_request(
        request,
        repo_root=root,
        verify_input=verify_input,
    )
    return request, root


def _enum_value(value: object) -> str:
    resolved = getattr(value, "value", value)
    return str(resolved)


def _select_run(
    request: Any,
    run_id: str,
    *,
    model_family: str | None = None,
    adaptation_mode: str | None = None,
) -> Any:
    matches = tuple(item for item in request.runs if item.run_id == run_id)
    if len(matches) != 1:
        raise ValueError("--run-id must name exactly one frozen full run")
    selected = matches[0]
    if _enum_value(selected.run_kind) != "full" or selected.step_origin != 0:
        raise ValueError("Phase 40 external execution accepts fresh full runs only")
    if selected.probe_parent is not None:
        raise ValueError("Phase 40 external full runs cannot have probe lineage")
    if model_family is not None and _enum_value(selected.model_family) != model_family:
        raise ValueError("run ID model family differs from the requested command")
    if adaptation_mode is not None and _enum_value(selected.adaptation_mode) != adaptation_mode:
        raise ValueError("run ID adaptation mode differs from the requested command")
    template = request.control_template_by_run.get(run_id)
    if template is None or request.control_template_digest_by_run.get(run_id) != template.sha256:
        raise ValueError("run ID is missing its exact frozen control template")
    return selected


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def _verify_materialized_input(input_root: Path, reference: Any) -> None:
    expected_root = Path(reference.extraction_root)
    if not _same_path(input_root, expected_root):
        raise ValueError("--input-root/--extraction-root is not request-bound")
    root = _lexical_absolute(input_root)
    if not root.is_dir() or root.is_symlink():
        raise FileNotFoundError(f"verified input root is missing or unsafe: {root}")
    members = tuple(reference.data_members)
    if tuple(member.member_name for member in members) != ("train.jsonl", "val.jsonl"):
        raise ValueError("request input data-member order is not train then validation")
    for member in members:
        path = root / member.member_name
        if not path.is_file() or path.is_symlink():
            raise FileNotFoundError(f"materialized input member is missing or unsafe: {path}")
        if path.stat().st_size != member.bytes or _sha256_file(path) != member.sha256:
            raise RuntimeError(f"materialized input identity mismatch: {member.member_name}")


def _sanitize_raw_argv(raw_argv: Sequence[str]) -> tuple[str, ...]:
    evidence = _import_module("src.model_adaptation.phase40_evidence")
    return evidence.sanitize_argv(tuple(raw_argv))


def _verify_input_archive(
    *,
    request: Any,
    archive_path: Path,
    repo_root: Path,
    extraction_root: Path,
    materialize: bool = True,
) -> Any:
    handoff = _import_module("src.model_adaptation.phase40_handoff")
    return handoff.verify_phase40_input_bundle(
        Path(archive_path),
        request.input_bundle,
        repo_root=Path(repo_root),
        extraction_root=Path(extraction_root),
        materialize=materialize,
    )


def _package_version(distribution: str) -> str:
    try:
        return importlib.metadata.version(distribution)
    except importlib.metadata.PackageNotFoundError as exc:
        raise RuntimeError(f"required package is not installed: {distribution}") from exc


def _runtime_capabilities(model_family: str, adaptation_mode: str) -> dict[str, object]:
    required = dict(
        _PHOBERT_DEPENDENCIES if model_family == "phobert" else _QWEN_DEPENDENCIES
    )
    if adaptation_mode == "qlora":
        required["bitsandbytes"] = "0.50.1"
    installed: dict[str, str] = {}
    for distribution, expected in sorted(required.items()):
        actual = _package_version(distribution)
        if actual != expected:
            raise RuntimeError(
                f"package version mismatch for {distribution}: expected {expected}, got {actual}"
            )
        installed[distribution] = actual

    import_names = {
        "accelerate": "accelerate",
        "huggingface-hub": "huggingface_hub",
        "peft": "peft",
        "pydantic": "pydantic",
        "pydantic-settings": "pydantic_settings",
        "scikit-learn": "sklearn",
        "torch": "torch",
        "transformers": "transformers",
        "underthesea": "underthesea",
        "bitsandbytes": "bitsandbytes",
    }
    for distribution in required:
        module_name = import_names[distribution]
        if importlib.util.find_spec(module_name) is None:
            raise RuntimeError(f"required package is not importable: {distribution}")

    torch_module = _import_module("torch")
    cuda = getattr(torch_module, "cuda", None)
    cuda_available = bool(cuda is not None and cuda.is_available())
    if not cuda_available:
        raise RuntimeError("Phase 40 external full runs require an available CUDA accelerator")

    transformers = _import_module("transformers")
    common_transformers = (
        "AutoTokenizer",
        "Trainer",
        "TrainingArguments",
    )
    if any(getattr(transformers, name, None) is None for name in common_transformers):
        raise RuntimeError("Transformers runtime lacks the required Trainer/tokenizer surface")
    if model_family == "qwen":
        peft = _import_module("peft")
        if getattr(transformers, "AutoModelForCausalLM", None) is None:
            raise RuntimeError("Transformers runtime lacks AutoModelForCausalLM")
        if any(getattr(peft, name, None) is None for name in ("LoraConfig", "get_peft_model")):
            raise RuntimeError("PEFT runtime lacks the required LoRA surface")
        if adaptation_mode == "qlora":
            bitsandbytes = _import_module("bitsandbytes")
            linear4bit = getattr(getattr(bitsandbytes, "nn", None), "Linear4bit", None)
            if not isinstance(linear4bit, type):
                raise RuntimeError("bitsandbytes runtime lacks nn.Linear4bit")
            if getattr(transformers, "BitsAndBytesConfig", None) is None or getattr(
                peft, "prepare_model_for_kbit_training", None
            ) is None:
                raise RuntimeError("QLoRA runtime lacks its quantization preparation surface")
    else:
        underthesea = _import_module("underthesea")
        if getattr(transformers, "AutoModelForSequenceClassification", None) is None:
            raise RuntimeError(
                "Transformers runtime lacks AutoModelForSequenceClassification"
            )
        if getattr(transformers, "DataCollatorWithPadding", None) is None:
            raise RuntimeError("Transformers runtime lacks DataCollatorWithPadding")
        if not callable(getattr(underthesea, "word_tokenize", None)):
            raise RuntimeError("underthesea runtime lacks word_tokenize")
    return {
        "cuda_available": True,
        "dependencies": installed,
        "model_acquisition_performed": False,
        "training_performed": False,
    }


def _canonical_base_model_paths(repo_root: Path, model_family: str) -> tuple[Path, Path]:
    """Return the only local snapshot and manifest paths accepted for a family."""

    try:
        relative = _BASE_MODEL_RELATIVE_PATHS[model_family]
    except KeyError as exc:
        raise ValueError(f"unsupported Phase 40 model family: {model_family}") from exc
    root = _lexical_absolute(Path(repo_root))
    snapshot = _lexical_absolute(root / relative)
    try:
        snapshot.relative_to(root)
    except ValueError as exc:
        raise ValueError("canonical base-model path escapes the repository root") from exc
    manifest = _lexical_absolute(root / _BASE_MODEL_MANIFEST_RELATIVE_PATHS[model_family])
    try:
        manifest.relative_to(root)
    except ValueError as exc:
        raise ValueError("canonical base-model manifest path escapes the repository root") from exc
    return snapshot, manifest


def _require_safe_path_chain(path: Path, *, anchor: Path) -> None:
    """Reject a path whose existing anchor/descendant components are symlinks."""

    target = _lexical_absolute(path)
    root = _lexical_absolute(anchor)
    try:
        relative = target.relative_to(root)
    except ValueError as exc:
        raise ValueError("base-model path is outside the canonical repository root") from exc
    for ancestor in (root, *root.parents):
        if ancestor.exists() and ancestor.is_symlink():
            raise ValueError(
                "repository root for base-model acquisition must not traverse a symlink"
            )
    current = root
    for component in relative.parts:
        current /= component
        if current.exists() and current.is_symlink():
            raise ValueError("base-model path must not traverse a symbolic link")


def _model_backend_contract(model_family: str) -> tuple[ModuleType, Any, Any, Any]:
    if model_family == "qwen":
        backend = _import_module("src.model_adaptation.training")
        names = (
            "build_qwen_base_model_acquisition_request",
            "seal_qwen_base_model_snapshot",
            "validate_qwen_base_model_snapshot",
        )
    elif model_family == "phobert":
        backend = _import_module("src.model_adaptation.phobert_training")
        names = (
            "build_phobert_base_model_acquisition_request",
            "seal_phobert_base_model_snapshot",
            "validate_phobert_base_model_snapshot",
        )
    else:
        raise ValueError(f"unsupported Phase 40 model family: {model_family}")
    functions = tuple(getattr(backend, name, None) for name in names)
    if not all(callable(function) for function in functions):
        raise RuntimeError(f"{model_family} backend lacks the sealed model-acquisition contract")
    return backend, functions[0], functions[1], functions[2]


def _request_model_identity(request: Any, selected_run: Any) -> tuple[str, str]:
    controlled = request.control_template_by_run[
        selected_run.run_id
    ].materialize_for_validation()
    model_id = getattr(controlled, "model_id", None)
    model_revision = getattr(controlled, "model_revision", None)
    if not isinstance(model_id, str) or not model_id:
        raise ValueError("run request lacks one exact model ID")
    if not isinstance(model_revision, str) or not re.fullmatch(r"[0-9a-f]{40}", model_revision):
        raise ValueError("run request lacks one immutable model revision")
    additional = {
        getattr(item, "name", None): getattr(item, "value", None)
        for item in getattr(controlled, "additional_controls", ())
    }
    if additional.get("local_files_only") is not True:
        raise ValueError("Phase 40 training must load only the verified local model snapshot")
    if _enum_value(selected_run.model_family) == "qwen" and additional.get(
        "trust_remote_code"
    ) is not False:
        raise ValueError("Phase 40 Qwen training forbids remote model code")
    return model_id, model_revision


def _validate_base_model_cli_paths(
    *,
    repo_root: Path,
    model_family: str,
    base_model_path: Path,
    base_model_manifest_path: Path,
    model_id: str,
    model_revision: str,
) -> Any:
    canonical_snapshot, canonical_manifest = _canonical_base_model_paths(
        repo_root,
        model_family,
    )
    if not _same_path(base_model_path, canonical_snapshot):
        raise ValueError("--base-model-path is not the canonical request-bound snapshot path")
    if not _same_path(base_model_manifest_path, canonical_manifest):
        raise ValueError("--base-model-manifest-path is not the canonical provenance path")
    _require_safe_path_chain(canonical_snapshot, anchor=repo_root)
    if not canonical_manifest.is_file() or canonical_manifest.is_symlink():
        raise RuntimeError("base-model provenance manifest is missing or unsafe")
    _, _, _, validator = _model_backend_contract(model_family)
    return validator(
        canonical_snapshot,
        manifest_path=canonical_manifest,
        expected_model_id=model_id,
        expected_model_revision=model_revision,
    )


def handle_acquire_model(args: argparse.Namespace) -> int:
    """Perform the one explicitly authorized network action in a later operator run."""

    if args.authorize_model_acquisition is not True:
        raise RuntimeError("model acquisition requires --authorize-model-acquisition")
    request, repo_root = _load_verified_request(
        args.request_path,
        repo_root=args.repo_root,
        verify_input=False,
    )
    selected = _select_run(request, args.run_id)
    model_family = _enum_value(selected.model_family)
    model_id, model_revision = _request_model_identity(request, selected)
    snapshot_path, manifest_path = _canonical_base_model_paths(repo_root, model_family)
    _require_safe_path_chain(snapshot_path, anchor=repo_root)
    if _package_version("huggingface-hub") != "1.16.1":
        raise RuntimeError("model acquisition requires exact huggingface-hub==1.16.1")
    _, request_builder, sealer, validator = _model_backend_contract(model_family)

    acquired = False
    if snapshot_path.exists():
        if not snapshot_path.is_dir() or snapshot_path.is_symlink():
            raise RuntimeError("canonical base-model snapshot path is not a safe directory")
        snapshot = validator(
            snapshot_path,
            manifest_path=manifest_path,
            expected_model_id=model_id,
            expected_model_revision=model_revision,
        )
    else:
        snapshot_path.parent.mkdir(parents=True, exist_ok=True)
        _require_safe_path_chain(snapshot_path.parent, anchor=repo_root)
        acquisition = request_builder(
            snapshot_path,
            model_id=model_id,
            model_revision=model_revision,
        )
        download_kwargs = dict(acquisition.snapshot_download_kwargs())
        expected_download_kwargs = {
            "repo_id": model_id,
            "revision": model_revision,
            "local_dir": os.fspath(snapshot_path),
        }
        if download_kwargs != expected_download_kwargs:
            raise RuntimeError("backend model-acquisition request is not exactly request-bound")
        hub = _import_module("huggingface_hub")
        snapshot_download = getattr(hub, "snapshot_download", None)
        if not callable(snapshot_download):
            raise RuntimeError("huggingface-hub lacks snapshot_download")
        download_kwargs.update(
            {
                "force_download": False,
                "local_files_only": False,
                "token": False,
            }
        )
        downloaded_path = Path(snapshot_download(**download_kwargs))
        if not _same_path(downloaded_path, snapshot_path):
            raise RuntimeError("model acquisition returned a non-canonical snapshot path")
        sealer(
            snapshot_path,
            manifest_path=manifest_path,
            model_id=model_id,
            model_revision=model_revision,
        )
        snapshot = validator(
            snapshot_path,
            manifest_path=manifest_path,
            expected_model_id=model_id,
            expected_model_revision=model_revision,
        )
        acquired = True
    if not manifest_path.is_file() or manifest_path.is_symlink():
        raise RuntimeError("sealed model acquisition did not produce its canonical manifest")
    print(
        json.dumps(
            {
                "manifest_path": os.fspath(manifest_path),
                "manifest_sha256": snapshot.manifest_sha256,
                "model_acquisition_performed": acquired,
                "model_family": model_family,
                "model_id": model_id,
                "model_revision": model_revision,
                "snapshot_content_sha256": snapshot.snapshot_content_sha256,
                "snapshot_path": os.fspath(snapshot_path),
                "verified": True,
            },
            sort_keys=True,
        )
    )
    return 0


def _verify_qwen_resume_checkpoint(
    checkpoint: Path,
    *,
    request: Any,
    selected_run: Any,
    repo_root: Path,
    base_model_path: Path,
    base_model_manifest_path: Path,
) -> dict[str, object]:
    training = _import_module("src.model_adaptation.training")
    evidence = _import_module("src.model_adaptation.phase40_evidence")
    manifest_name = training.PHASE40_RESUME_MANIFEST_NAME
    payload = _read_json_object(checkpoint / manifest_name)
    controlled_payload = payload.get("controlled_config")
    if not isinstance(controlled_payload, dict):
        raise RuntimeError("checkpoint resume manifest lacks controlled_config")
    controlled = evidence.ResumeControlledConfig.model_validate(controlled_payload)
    request.control_template_by_run[selected_run.run_id].verify_runtime_config(controlled)
    model_id, model_revision = _request_model_identity(request, selected_run)
    base_model_snapshot = _validate_base_model_cli_paths(
        repo_root=repo_root,
        model_family="qwen",
        base_model_path=base_model_path,
        base_model_manifest_path=base_model_manifest_path,
        model_id=model_id,
        model_revision=model_revision,
    )
    event_path = _lexical_absolute(
        Path(repo_root) / selected_run.returned_root / "events.jsonl"
    )
    training._read_checkpoint_resume_manifest(  # noqa: SLF001 - exact backend verifier
        checkpoint,
        controlled_config=controlled,
        event_path=event_path,
        base_model_snapshot=base_model_snapshot,
        require_cumulative_history=True,
    )
    return payload


def _verify_phobert_resume_checkpoint(
    checkpoint: Path,
    *,
    phobert: ModuleType,
    config: Any,
    controlled_config: Any,
    validation_snapshot: Any,
    base_model_snapshot: Any | None = None,
) -> dict[str, object]:
    verifier = getattr(phobert, "verify_phobert_resume_checkpoint", None)
    if not callable(verifier):
        raise RuntimeError("PhoBERT backend does not expose exact resume verification")
    manifest, _ = verifier(
        checkpoint,
        config=config,
        controlled_config=controlled_config,
        validation_snapshot=validation_snapshot,
        base_model_snapshot=base_model_snapshot,
    )
    return manifest.model_dump(mode="json")


def _verify_resume_checkpoint(
    checkpoint: Path,
    *,
    request: Any,
    selected_run: Any,
    repo_root: Path,
    base_model_path: Path,
    base_model_manifest_path: Path,
) -> dict[str, object]:
    if str(checkpoint).casefold() == "latest" or Path(checkpoint).name.casefold() == "latest":
        raise ValueError("lexical latest resume is forbidden; provide one exact checkpoint-N")
    checkpoint = _lexical_absolute(checkpoint)
    match = _CHECKPOINT_PATTERN.fullmatch(checkpoint.name)
    if not match or not checkpoint.is_dir() or checkpoint.is_symlink():
        raise ValueError("resume target must be one existing non-symlink checkpoint-N directory")
    if any(path.is_symlink() for path in checkpoint.rglob("*")):
        raise ValueError("resume checkpoint must not contain symlinks")
    family = _enum_value(selected_run.model_family)
    if family == "qwen":
        if selected_run.run_id not in checkpoint.parts:
            raise ValueError("Qwen resume checkpoint is outside its run-ID work root")
        return _verify_qwen_resume_checkpoint(
            checkpoint,
            request=request,
            selected_run=selected_run,
            repo_root=repo_root,
            base_model_path=base_model_path,
            base_model_manifest_path=base_model_manifest_path,
        )
    if family == "phobert":
        raise RuntimeError("PhoBERT exact resume verification requires its canonical data contract")
    raise ValueError("unsupported model family in resume request")


def handle_verify_input_bundle(args: argparse.Namespace) -> int:
    handoff = _import_module("src.model_adaptation.phase40_handoff")
    reference = handoff.InputBundleReference.model_validate(
        _read_json_object(args.reference_path)
    )
    contract = handoff.verify_phase40_input_bundle(
        args.archive_path,
        reference,
        repo_root=args.repo_root,
        extraction_root=args.extraction_root,
        materialize=not args.verify_only,
    )
    print(
        json.dumps(
            {
                "archive_sha256": reference.archive_sha256,
                "materialized": not args.verify_only,
                "train_records": len(contract.train_snapshot.rows),
                "validation_records": len(contract.validation_snapshot.rows),
                "verified": True,
            },
            sort_keys=True,
        )
    )
    return 0


def handle_verify_run_request(args: argparse.Namespace) -> int:
    request, _ = _load_verified_request(
        args.request_path,
        repo_root=args.repo_root,
        verify_input=args.verify_input,
    )
    print(
        json.dumps(
            {
                "input_archive_verified": args.verify_input,
                "run_ids": sorted(run.run_id for run in request.runs),
                "source_archive_verified": True,
                "verified": True,
            },
            sort_keys=True,
        )
    )
    return 0


def handle_doctor(args: argparse.Namespace) -> int:
    request, repo_root = _load_verified_request(
        args.run_request_path,
        repo_root=args.repo_root,
        verify_input=False,
    )
    candidates = tuple(
        run
        for run in request.runs
        if _enum_value(run.model_family) == args.model_family
        and _enum_value(run.adaptation_mode) == args.adaptation_mode
    )
    if len(candidates) != 1:
        raise ValueError("doctor identity does not name one frozen request run")
    selected = _select_run(
        request,
        candidates[0].run_id,
        model_family=args.model_family,
        adaptation_mode=args.adaptation_mode,
    )
    if args.run_kind != "full":
        raise ValueError("external doctor accepts full runs only")
    controlled = request.control_template_by_run[selected.run_id].materialize_for_validation()
    if controlled.model_revision != args.model_revision:
        raise ValueError("doctor model revision differs from the frozen request")
    model_id, model_revision = _request_model_identity(request, selected)
    base_model_snapshot = _validate_base_model_cli_paths(
        repo_root=repo_root,
        model_family=args.model_family,
        # Keep the recorded argv relative/sanitized while giving the training
        # backend the normalized absolute snapshot paths its provenance gate
        # requires.  This matters on Windows, where a D-drive local transfer
        # package cannot place personal absolute paths in immutable evidence.
        base_model_path=_lexical_absolute(args.base_model_path),
        base_model_manifest_path=_lexical_absolute(args.base_model_manifest_path),
        model_id=model_id,
        model_revision=model_revision,
    )
    _verify_materialized_input(args.input_root, request.input_bundle)
    capabilities = _runtime_capabilities(args.model_family, args.adaptation_mode)
    print(
        json.dumps(
            {
                **capabilities,
                "adaptation_mode": args.adaptation_mode,
                "input_identity_verified": True,
                "model_family": args.model_family,
                "model_manifest_sha256": base_model_snapshot.manifest_sha256,
                "model_revision": args.model_revision,
                "model_snapshot_content_sha256": base_model_snapshot.snapshot_content_sha256,
                "model_snapshot_verified": True,
                "request_identity_verified": True,
                "run_id": selected.run_id,
            },
            sort_keys=True,
        )
    )
    return 0


def handle_verify_resume(args: argparse.Namespace) -> int:
    request, repo_root = _load_verified_request(
        args.request_path,
        repo_root=args.repo_root,
        verify_input=False,
    )
    selected = _select_run(request, args.run_id)
    _verify_materialized_input(args.input_root, request.input_bundle)
    model_family = _enum_value(selected.model_family)
    model_id, model_revision = _request_model_identity(request, selected)
    base_model_snapshot = _validate_base_model_cli_paths(
        repo_root=repo_root,
        model_family=model_family,
        base_model_path=args.base_model_path,
        base_model_manifest_path=args.base_model_manifest_path,
        model_id=model_id,
        model_revision=model_revision,
    )
    if model_family == "phobert":
        contract = _verify_input_archive(
            request=request,
            archive_path=Path(request.input_bundle.drive_path),
            repo_root=repo_root,
            extraction_root=args.input_root,
            materialize=False,
        )
        checkpoint = _lexical_absolute(args.checkpoint)
        if not _CHECKPOINT_PATTERN.fullmatch(checkpoint.name):
            raise ValueError("resume target must be one exact checkpoint-N directory")
        work_root = checkpoint.parent.parent
        phobert = _import_module("src.model_adaptation.phobert_training")
        raw_argv = _sanitize_raw_argv(args._phase40_raw_argv)
        config = _phobert_config_from_request(
            phobert=phobert,
            request=request,
            selected=selected,
            data_contract=contract,
            repo_root=repo_root,
            work_root=work_root,
            raw_argv=raw_argv,
            resume_from_checkpoint=checkpoint,
            base_model_path=args.base_model_path,
            base_model_manifest_path=args.base_model_manifest_path,
        )
        controlled = phobert.build_phobert_controlled_config(
            config,
            contract,
            accelerator=request.control_template_by_run[
                selected.run_id
            ].materialize_for_validation().accelerator,
        )
        payload = _verify_phobert_resume_checkpoint(
            checkpoint,
            phobert=phobert,
            config=config,
            controlled_config=controlled,
            validation_snapshot=contract.validation_snapshot,
            base_model_snapshot=base_model_snapshot,
        )
    else:
        payload = _verify_resume_checkpoint(
            args.checkpoint,
            request=request,
            selected_run=selected,
            repo_root=repo_root,
            base_model_path=args.base_model_path,
            base_model_manifest_path=args.base_model_manifest_path,
        )
    print(
        json.dumps(
            {
                "checkpoint_step": payload.get("checkpoint_step"),
                "input_identity_verified": True,
                "request_identity_verified": True,
                "resume_compatible": True,
                "run_id": selected.run_id,
            },
            sort_keys=True,
        )
    )
    return 0


def handle_train_qwen(args: argparse.Namespace) -> int:
    request, repo_root = _load_verified_request(
        args.request_path,
        repo_root=args.repo_root,
        verify_input=False,
    )
    selected = _select_run(
        request,
        args.run_id,
        model_family="qwen",
        adaptation_mode=args.adaptation_mode,
    )
    if args.run_kind != "full":
        raise ValueError("Phase 40 Qwen external training accepts full runs only")
    model_id, model_revision = _request_model_identity(request, selected)
    _validate_base_model_cli_paths(
        repo_root=repo_root,
        model_family="qwen",
        base_model_path=args.base_model_path,
        base_model_manifest_path=args.base_model_manifest_path,
        model_id=model_id,
        model_revision=model_revision,
    )
    raw_argv = _sanitize_raw_argv(args._phase40_raw_argv)
    contract = _verify_input_archive(
        request=request,
        archive_path=args.input_archive,
        repo_root=repo_root,
        extraction_root=args.extraction_root,
    )
    if args.resume_from_checkpoint is not None:
        _verify_resume_checkpoint(
            args.resume_from_checkpoint,
            request=request,
            selected_run=selected,
            repo_root=repo_root,
            base_model_path=args.base_model_path,
            base_model_manifest_path=args.base_model_manifest_path,
        )
    training = _import_module("src.model_adaptation.training")
    config = training.build_phase40_qwen_training_config(
        run_request=request,
        run_id=selected.run_id,
        data_contract=contract,
        repo_root=repo_root,
        work_root=_lexical_absolute(args.output_root),
        base_model_path=_lexical_absolute(args.base_model_path),
        base_model_manifest_path=_lexical_absolute(args.base_model_manifest_path),
        sanitized_argv=raw_argv,
        resume_from_checkpoint=(
            None
            if args.resume_from_checkpoint is None
            else os.fspath(_lexical_absolute(args.resume_from_checkpoint))
        ),
        device=args.device,
    )
    result = training.run_phase40_qwen_training(
        config,
        data_contract=contract,
        run_request=request,
        repo_root=repo_root,
    )
    evidence = result["verified_evidence"]
    print(
        json.dumps(
            {
                "run_id": selected.run_id,
                "run_root": selected.returned_root,
                "safety_gate_passed": bool(result["safety_gate_passed"]),
                "status": _enum_value(evidence.status),
                "verified": True,
            },
            sort_keys=True,
        )
    )
    return 0


def _phobert_config_from_request(
    *,
    phobert: ModuleType,
    request: Any,
    selected: Any,
    data_contract: Any,
    repo_root: Path,
    work_root: Path,
    raw_argv: tuple[str, ...],
    resume_from_checkpoint: Path | None,
    base_model_path: Path,
    base_model_manifest_path: Path,
) -> Any:
    template = request.control_template_by_run[selected.run_id]
    controlled = template.materialize_for_validation()
    if _enum_value(controlled.experiment_identity.model_family) != "phobert":
        raise ValueError("PhoBERT request template has the wrong model family")
    additional = {item.name: item.value for item in controlled.additional_controls}
    local_files_only = additional.get("local_files_only")
    if not isinstance(local_files_only, bool):
        raise ValueError("PhoBERT request lacks a boolean local_files_only control")
    if controlled.world_size != 1:
        raise ValueError("PhoBERT operator currently requires the frozen single-device world size")
    cadence = controlled.cadence
    if cadence.save_steps != cadence.evaluation_steps:
        raise ValueError("PhoBERT save and evaluation cadence must remain identical")
    kwargs: dict[str, object] = {
        "run_id": selected.run_id,
        "run_bundle_root": _lexical_absolute(repo_root / selected.returned_root),
        "transfer_authority": _import_module(
            "src.model_adaptation.phase40_handoff"
        ).transfer_authority_from_request(request),
        "sanitized_argv": raw_argv,
        "local_base_model_path": _lexical_absolute(base_model_path),
        "base_model_provenance_path": _lexical_absolute(base_model_manifest_path),
        "model_id": controlled.model_id,
        "model_revision": controlled.model_revision,
        "seed": controlled.seed,
        "data_seed": controlled.data_seed,
        "max_length": controlled.max_sequence_length,
        "per_device_train_batch_size": controlled.per_device_train_batch_size,
        "gradient_accumulation_steps": controlled.gradient_accumulation_steps,
        "num_train_epochs": controlled.num_train_epochs,
        "max_optimizer_steps": controlled.max_optimizer_steps,
        "learning_rate": controlled.optimizer.learning_rate,
        "weight_decay": controlled.optimizer.weight_decay,
        "optimizer_name": controlled.optimizer.optimizer,
        "lr_scheduler_type": controlled.optimizer.lr_scheduler_type,
        "warmup_steps": controlled.optimizer.warmup_steps,
        "warmup_ratio": controlled.optimizer.warmup_ratio,
        "max_grad_norm": controlled.optimizer.max_grad_norm,
        "logging_steps": cadence.logging_steps,
        "evaluation_steps": cadence.evaluation_steps,
        "save_total_limit": cadence.save_total_limit,
        "gradient_checkpointing": controlled.gradient_checkpointing,
        "bf16": controlled.precision.bf16,
        "fp16": controlled.precision.fp16,
        "tf32": controlled.precision.tf32,
        "local_files_only": local_files_only,
        "resume_from_checkpoint": resume_from_checkpoint,
    }
    fields = getattr(phobert.PhoBertTrainingConfig, "__dataclass_fields__", {})
    if "work_root" not in fields:
        raise RuntimeError(
            "PhoBERT backend lacks the explicit mutable work_root required by the operator"
        )
    kwargs["work_root"] = _lexical_absolute(work_root)
    config = phobert.PhoBertTrainingConfig(**kwargs)
    proposed = phobert.build_phobert_controlled_config(
        config,
        data_contract,
        accelerator=controlled.accelerator,
    )
    template.verify_runtime_config(proposed)
    return config

def handle_train_phobert(args: argparse.Namespace) -> int:
    request, repo_root = _load_verified_request(
        args.request_path,
        repo_root=args.repo_root,
        verify_input=False,
    )
    selected = _select_run(
        request,
        args.run_id,
        model_family="phobert",
        adaptation_mode="classification-head",
    )
    model_id, model_revision = _request_model_identity(request, selected)
    base_model_snapshot = _validate_base_model_cli_paths(
        repo_root=repo_root,
        model_family="phobert",
        base_model_path=args.base_model_path,
        base_model_manifest_path=args.base_model_manifest_path,
        model_id=model_id,
        model_revision=model_revision,
    )
    raw_argv = _sanitize_raw_argv(args._phase40_raw_argv)
    contract = _verify_input_archive(
        request=request,
        archive_path=args.input_archive,
        repo_root=repo_root,
        extraction_root=args.extraction_root,
    )
    resume = (
        None
        if args.resume_from_checkpoint is None
        else _lexical_absolute(args.resume_from_checkpoint)
    )
    if resume is not None:
        if not _CHECKPOINT_PATTERN.fullmatch(resume.name):
            raise ValueError("resume target must be one exact checkpoint-N directory")
    phobert = _import_module("src.model_adaptation.phobert_training")
    config = _phobert_config_from_request(
        phobert=phobert,
        request=request,
        selected=selected,
        data_contract=contract,
        repo_root=repo_root,
        work_root=args.output_root,
        raw_argv=raw_argv,
        resume_from_checkpoint=resume,
        base_model_path=args.base_model_path,
        base_model_manifest_path=args.base_model_manifest_path,
    )
    if resume is not None:
        controlled = phobert.build_phobert_controlled_config(
            config,
            contract,
            accelerator=request.control_template_by_run[
                selected.run_id
            ].materialize_for_validation().accelerator,
        )
        _verify_phobert_resume_checkpoint(
            resume,
            phobert=phobert,
            config=config,
            controlled_config=controlled,
            validation_snapshot=contract.validation_snapshot,
            base_model_snapshot=base_model_snapshot,
        )
    result = phobert.run_phobert_training(
        config,
        contract,
        requested_control_template=request.control_template_by_run[selected.run_id],
    )
    print(
        json.dumps(
            {
                "run_id": selected.run_id,
                "run_root": selected.returned_root,
                "safety_gate_passed": bool(result.selection.safety_gate_passed),
                "status": _enum_value(result.evidence.status),
                "verified": True,
            },
            sort_keys=True,
        )
    )
    return 0


def handle_verify_run_evidence(args: argparse.Namespace) -> int:
    evidence_api = _import_module("src.model_adaptation.phase40_evidence")
    evidence = evidence_api.verify_phase40_bundle(args.run_root)
    print(
        json.dumps(
            {
                "run_id": evidence.run_id,
                "status": _enum_value(evidence.status),
                "verified": True,
            },
            sort_keys=True,
        )
    )
    return 0


def handle_render_graphs(args: argparse.Namespace) -> int:
    evidence_api = _import_module("src.model_adaptation.phase40_evidence")
    graphs = _import_module("src.model_adaptation.phase40_graphs")
    before = evidence_api.verify_phase40_bundle(args.run_root)
    provenance = graphs.render_phase40_graphs(
        args.run_root,
        smoothing_window=args.smoothing_window,
        dpi=args.dpi,
    )
    after = evidence_api.verify_phase40_bundle(args.run_root)
    if before != after:
        raise RuntimeError("graph regeneration changed the signed run evidence")
    print(
        json.dumps(
            {
                "graph_id": provenance.graph_id,
                "run_id": after.run_id,
                "verified": True,
            },
            sort_keys=True,
        )
    )
    return 0


def handle_validate_notebooks(args: argparse.Namespace) -> int:
    notebooks = _import_module("src.model_adaptation.phase40_notebooks")
    issues = tuple(notebooks.validate_phase40_notebooks(args.root))
    if issues:
        for issue in issues:
            print(str(issue), file=sys.stderr)
        return 1
    print(json.dumps({"root": os.fspath(args.root), "validated": 3}, sort_keys=True))
    return 0


def handle_local_decision(args: argparse.Namespace) -> int:
    """Delegate one typed local stage without importing training at CLI load time."""

    local = _import_module("src.model_adaptation.phase40_local_experiment")
    result = local.run_operator_stage(args)
    if not isinstance(result, dict):
        raise RuntimeError("local decision stage did not return a JSON object")
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


def _add_request_root_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--request-path", type=Path, required=True)
    parser.add_argument("--repo-root", type=Path, default=None)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="phase40-operator",
        description="Slim archive-closed Phase 40 Colab operator",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    verify_input = subparsers.add_parser("phase40-verify-input-bundle")
    verify_input.add_argument("--archive-path", type=Path, required=True)
    verify_input.add_argument("--reference-path", type=Path, required=True)
    verify_input.add_argument("--repo-root", type=Path, required=True)
    verify_input.add_argument("--extraction-root", type=Path, required=True)
    verify_input.add_argument("--verify-only", action="store_true")
    verify_input.set_defaults(handler=handle_verify_input_bundle)

    verify_request = subparsers.add_parser("phase40-verify-run-request")
    _add_request_root_arguments(verify_request)
    verify_request.add_argument("--verify-input", action="store_true")
    verify_request.set_defaults(handler=handle_verify_run_request)

    acquire_model = subparsers.add_parser("phase40-acquire-model")
    _add_request_root_arguments(acquire_model)
    acquire_model.add_argument("--run-id", required=True)
    acquire_model.add_argument("--authorize-model-acquisition", action="store_true")
    acquire_model.set_defaults(handler=handle_acquire_model)

    doctor = subparsers.add_parser("phase40-doctor")
    doctor.add_argument("--model-family", choices=("qwen", "phobert"), required=True)
    doctor.add_argument(
        "--adaptation-mode",
        choices=("lora", "qlora", "classification-head"),
        required=True,
    )
    doctor.add_argument("--run-kind", choices=("full",), required=True)
    doctor.add_argument("--model-revision", required=True)
    doctor.add_argument("--run-request-path", type=Path, required=True)
    doctor.add_argument("--repo-root", type=Path, default=None)
    doctor.add_argument("--input-root", type=Path, required=True)
    doctor.add_argument("--base-model-path", type=Path, required=True)
    doctor.add_argument("--base-model-manifest-path", type=Path, required=True)
    doctor.set_defaults(handler=handle_doctor)

    verify_resume = subparsers.add_parser("phase40-verify-resume")
    _add_request_root_arguments(verify_resume)
    verify_resume.add_argument("--run-id", required=True)
    verify_resume.add_argument("--checkpoint", type=Path, required=True)
    verify_resume.add_argument("--input-root", type=Path, required=True)
    verify_resume.add_argument("--base-model-path", type=Path, required=True)
    verify_resume.add_argument("--base-model-manifest-path", type=Path, required=True)
    verify_resume.set_defaults(handler=handle_verify_resume)

    train_qwen = subparsers.add_parser("phase40-train-qwen")
    train_qwen.add_argument("--adaptation-mode", choices=("lora", "qlora"), required=True)
    train_qwen.add_argument("--run-kind", choices=("full",), required=True)
    _add_request_root_arguments(train_qwen)
    train_qwen.add_argument("--input-archive", type=Path, required=True)
    train_qwen.add_argument("--extraction-root", type=Path, required=True)
    train_qwen.add_argument("--run-id", required=True)
    train_qwen.add_argument("--output-root", type=Path, required=True)
    train_qwen.add_argument("--base-model-path", type=Path, required=True)
    train_qwen.add_argument("--base-model-manifest-path", type=Path, required=True)
    train_qwen.add_argument("--resume-from-checkpoint", type=Path, default=None)
    train_qwen.add_argument("--device", choices=("auto", "cuda", "cpu"), default="auto")
    train_qwen.set_defaults(handler=handle_train_qwen)

    train_phobert = subparsers.add_parser("phase40-train-phobert")
    _add_request_root_arguments(train_phobert)
    train_phobert.add_argument("--input-archive", type=Path, required=True)
    train_phobert.add_argument("--extraction-root", type=Path, required=True)
    train_phobert.add_argument("--run-id", required=True)
    train_phobert.add_argument("--output-root", type=Path, required=True)
    train_phobert.add_argument("--base-model-path", type=Path, required=True)
    train_phobert.add_argument("--base-model-manifest-path", type=Path, required=True)
    train_phobert.add_argument("--resume-from-checkpoint", type=Path, default=None)
    train_phobert.set_defaults(handler=handle_train_phobert)

    verify_evidence = subparsers.add_parser("phase40-verify-run-evidence")
    verify_evidence.add_argument("--run-root", type=Path, required=True)
    verify_evidence.set_defaults(handler=handle_verify_run_evidence)

    graphs = subparsers.add_parser("phase40-render-graphs")
    graphs.add_argument("--run-root", type=Path, required=True)
    graphs.add_argument("--smoothing-window", type=int, default=None)
    graphs.add_argument("--dpi", type=int, default=120)
    graphs.set_defaults(handler=handle_render_graphs)

    validate_notebooks = subparsers.add_parser("phase40-validate-notebooks")
    validate_notebooks.add_argument("--root", type=Path, required=True)
    validate_notebooks.set_defaults(handler=handle_validate_notebooks)

    local_decision = subparsers.add_parser(
        "phase40-local-decision",
        help="run one stage of the bounded RTX 5050 LoRA/QLoRA decision experiment",
    )
    local_decision.add_argument(
        "--stage",
        choices=(
            "preflight",
            "record-authority",
            "lora",
            "lora-retry-1",
            "verify-package",
            "qlora",
            "finalize",
            "verify",
        ),
        required=True,
    )
    local_decision.add_argument("--decision-root", type=Path, required=True)
    local_decision.add_argument("--repo-root", type=Path, default=None)
    local_decision.add_argument("--train-split", type=Path, default=None)
    local_decision.add_argument("--val-split", type=Path, default=None)
    local_decision.add_argument("--downstream-contract", type=Path, default=None)
    local_decision.add_argument("--base-model-path", type=Path, default=None)
    local_decision.add_argument("--download-manifest", type=Path, default=None)
    local_decision.add_argument(
        "--model-id", default="Qwen/Qwen3-4B-Instruct-2507"
    )
    local_decision.add_argument(
        "--model-revision",
        default="cdbee75f17c01a7cc42f958dc650907174af0554",
    )
    local_decision.add_argument("--decision-window-seconds", type=float, default=7200.0)
    local_decision.add_argument("--lora-soft-limit-seconds", type=float, default=1800.0)
    local_decision.add_argument("--lora-hard-limit-seconds", type=float, default=3600.0)
    local_decision.add_argument("--warmup-steps", type=int, default=5)
    local_decision.add_argument("--evidence-target-steps", type=int, default=40)
    local_decision.add_argument("--post-warmup-steps", type=int, default=40)
    local_decision.add_argument("--authority-decision", default=None)
    local_decision.set_defaults(handler=handle_local_decision)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    raw_argv = tuple(sys.argv[1:] if argv is None else argv)
    args = build_parser().parse_args(raw_argv)
    args._phase40_raw_argv = raw_argv
    try:
        return int(args.handler(args))
    except (ImportError, OSError, RuntimeError, TypeError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
