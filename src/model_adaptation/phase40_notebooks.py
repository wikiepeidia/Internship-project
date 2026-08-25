"""Fail-closed static validation for the three Phase 40 Colab controllers.

The notebooks are deliberately boring.  They bootstrap only enough standard
library code to authenticate the repository source archive before importing
it, then delegate input verification, training, evidence, and graph work to
repository commands.  This module never executes a notebook.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
from typing import Any, Iterable, Mapping


NOTEBOOK_SCHEMA_VERSION = "phase40-notebook-controller-v1"
FIXED_SOURCE_ARCHIVE_PATH = "data/models/phase40/source/phase40-source.zip"
FIXED_SOURCE_INVENTORY_PATH = (
    "data/models/phase40/source/phase40-source-manifest.json"
)
FIXED_SOURCE_EXTRACTION_ROOT = "/content/phase40-source-v1"
FIXED_INPUT_DRIVE_PATH = (
    "/content/drive/MyDrive/internship-phase40/phase40-train-validation.zip"
)
FIXED_INPUT_EXTRACTION_ROOT = "/content/phase40-input-v1"
FIXED_INPUT_MEMBERS = (
    "phase40-input-manifest.json",
    "train.jsonl",
    "val.jsonl",
)
FIXED_TRANSFER_REPOSITORY_ROOT = (
    "/content/drive/MyDrive/internship-phase40/repository"
)
PINNED_QWEN_MODEL_ID = "Qwen/Qwen3-4B-Instruct-2507"
PINNED_QWEN_REVISION = "cdbee75f17c01a7cc42f958dc650907174af0554"
PINNED_PHOBERT_MODEL_ID = "vinai/phobert-base-v2"
PINNED_PHOBERT_REVISION = "e966aac8cb889325e073aa5f28ff70aca4dbc8c3"

COMMON_DEPENDENCY_PINS = (
    "torch==2.12.0+cu132",
    "transformers==5.9.0",
    "huggingface-hub==1.16.1",
    "accelerate==1.13.0",
    "pydantic==2.13.4",
    "pydantic-settings==2.14.1",
    "scikit-learn==1.8.0",
    "matplotlib==3.11.1",
)
QWEN_DEPENDENCY_PINS = (
    COMMON_DEPENDENCY_PINS[:2]
    + ("peft==0.19.1",)
    + COMMON_DEPENDENCY_PINS[2:]
)
QLORA_ONLY_PIN = "bitsandbytes==0.50.1"
PHOBERT_ONLY_PIN = "underthesea==9.5.0"
GGUF_PACKAGE_PIN = "gguf==0.19.0"
LLAMA_CPP_PYTHON_PIN = "llama-cpp-python==0.3.23"
TORCH_INDEX_URL = "https://download.pytorch.org/whl/cu132"
GGUF_CONVERTER_SHA256 = "f227273d926fd8ba1c5215ca9ba64d63e641b3277e6f225080b4aac434999b55"

_ROLE_LAYOUT = (
    ("overview", "markdown"),
    ("constants", "code"),
    ("drive-mount", "code"),
    ("package-authority", "code"),
    ("source-verify", "code"),
    ("source-extract", "code"),
    ("package-install", "code"),
    ("request-verify", "code"),
    ("model-acquire", "code"),
    ("input-verify", "code"),
    ("doctor", "code"),
    ("resume-policy", "code"),
    ("full-run", "code"),
    ("evidence-verify", "code"),
    ("graph-regenerate", "code"),
    ("bundle-export", "code"),
)
_QWEN_GGUF_ROLE_LAYOUT = (
    ("gguf-authority", "code"),
    ("gguf-export", "code"),
    ("optional-download", "code"),
)


@dataclass(frozen=True, slots=True)
class _NotebookSpec:
    filename: str
    model_family: str
    adaptation_mode: str
    model_id: str
    model_revision: str
    run_command: str
    dependency_pins: tuple[str, ...]
    returned_root: str
    model_relative_path: str
    model_manifest_relative_path: str
    gguf_slug: str | None = None


_SPECS: dict[str, _NotebookSpec] = {
    "qwen_lora_colab.ipynb": _NotebookSpec(
        filename="qwen_lora_colab.ipynb",
        model_family="qwen",
        adaptation_mode="lora",
        model_id=PINNED_QWEN_MODEL_ID,
        model_revision=PINNED_QWEN_REVISION,
        run_command="phase40-train-qwen",
        dependency_pins=QWEN_DEPENDENCY_PINS + (GGUF_PACKAGE_PIN, LLAMA_CPP_PYTHON_PIN),
        returned_root="data/models/phase40/full/qwen-lora",
        model_relative_path="data/models/phase40/base/qwen3-4b-instruct-2507",
        model_manifest_relative_path="data/models/phase40/base/qwen3-4b-instruct-2507.provenance.json",
        gguf_slug="qwen-lora-q8_0",
    ),
    "qwen_qlora_colab.ipynb": _NotebookSpec(
        filename="qwen_qlora_colab.ipynb",
        model_family="qwen",
        adaptation_mode="qlora",
        model_id=PINNED_QWEN_MODEL_ID,
        model_revision=PINNED_QWEN_REVISION,
        run_command="phase40-train-qwen",
        dependency_pins=QWEN_DEPENDENCY_PINS + (QLORA_ONLY_PIN, GGUF_PACKAGE_PIN, LLAMA_CPP_PYTHON_PIN),
        returned_root="data/models/phase40/full/qwen-qlora",
        model_relative_path="data/models/phase40/base/qwen3-4b-instruct-2507",
        model_manifest_relative_path="data/models/phase40/base/qwen3-4b-instruct-2507.provenance.json",
        gguf_slug="qwen-qlora-q8_0",
    ),
    "phobert_colab.ipynb": _NotebookSpec(
        filename="phobert_colab.ipynb",
        model_family="phobert",
        adaptation_mode="classification-head",
        model_id=PINNED_PHOBERT_MODEL_ID,
        model_revision=PINNED_PHOBERT_REVISION,
        run_command="phase40-train-phobert",
        dependency_pins=COMMON_DEPENDENCY_PINS + (PHOBERT_ONLY_PIN,),
        returned_root="data/models/phase40/full/phobert",
        model_relative_path="data/models/phase40/base/phobert-base-v2",
        model_manifest_relative_path="data/models/phase40/base/phobert-base-v2.provenance.json",
    ),
}

_CANONICAL_SOURCE_DIGESTS = {
    "phobert_colab.ipynb": "d18f4f59b3256afc3c41141f053857606c5d6699462593e3e56ef746b1acdee9",
    "qwen_lora_colab.ipynb": "388bd18091d5092262eab5e693bbf05d651e1f7b08c6698cf5ebeeec9dd10ab4",
    "qwen_qlora_colab.ipynb": "011e6bdebbbe27cb7129bde5be483eb8bd66eb086a073ef32d3a23293820a39e",
}


@dataclass(frozen=True, slots=True)
class NotebookValidationIssue:
    """One deterministic static-validation finding."""

    path: str
    code: str
    message: str
    cell_index: int | None = None

    def __str__(self) -> str:
        location = self.path
        if self.cell_index is not None:
            location += f":cell-{self.cell_index}"
        return f"{location}: {self.code}: {self.message}"


class _DuplicateJsonKey(ValueError):
    pass


def _reject_duplicate_keys(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise _DuplicateJsonKey(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _source_text(cell: Mapping[str, Any]) -> str:
    source = cell.get("source", "")
    if isinstance(source, str):
        return source
    if isinstance(source, list) and all(isinstance(item, str) for item in source):
        return "".join(source)
    raise ValueError("cell source must be a string or a list of strings")


def _normalized_source_sha256(notebook: Mapping[str, Any]) -> str:
    cells = notebook.get("cells", [])
    if not isinstance(cells, list):
        raise ValueError("cells must be a list")
    normalized = [
        {
            "cell_type": cell.get("cell_type"),
            "role": cell.get("metadata", {}).get("phase40_role"),
            "source": _source_text(cell),
        }
        for cell in cells
        if isinstance(cell, dict)
    ]
    payload = json.dumps(
        normalized,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _issue(
    path: Path,
    code: str,
    message: str,
    *,
    cell_index: int | None = None,
) -> NotebookValidationIssue:
    return NotebookValidationIssue(path.as_posix(), code, message, cell_index)


def _require_tokens(
    *,
    path: Path,
    source: str,
    role: str,
    cell_index: int,
    tokens: Iterable[str],
) -> list[NotebookValidationIssue]:
    return [
        _issue(
            path,
            f"missing-{role}-contract",
            f"{role} cell is missing required token {token!r}",
            cell_index=cell_index,
        )
        for token in tokens
        if token not in source
    ]


def _metadata_issue(
    path: Path,
    field: str,
    actual: object,
    expected: object,
) -> NotebookValidationIssue:
    return _issue(
        path,
        "metadata-contract",
        f"phase40 metadata {field!r} must be {expected!r}, got {actual!r}",
    )


def _validate_phase_metadata(
    path: Path,
    phase: object,
    spec: _NotebookSpec,
) -> list[NotebookValidationIssue]:
    if not isinstance(phase, dict):
        return [_issue(path, "metadata-contract", "missing phase40 metadata object")]
    expected: dict[str, object] = {
        "schema_version": NOTEBOOK_SCHEMA_VERSION,
        "model_family": spec.model_family,
        "adaptation_mode": spec.adaptation_mode,
        "run_kind": "full",
        "start_origin": "fresh-step-zero",
        "probe_parent": None,
        "model_id": spec.model_id,
        "model_revision": spec.model_revision,
        "dependency_pins": list(spec.dependency_pins),
        "source_archive_path": FIXED_SOURCE_ARCHIVE_PATH,
        "source_inventory_path": FIXED_SOURCE_INVENTORY_PATH,
        "source_extraction_root": FIXED_SOURCE_EXTRACTION_ROOT,
        "input_archive_drive_path": FIXED_INPUT_DRIVE_PATH,
        "input_extraction_root": FIXED_INPUT_EXTRACTION_ROOT,
        "input_members": list(FIXED_INPUT_MEMBERS),
        "returned_root": spec.returned_root,
        "model_repository_relative_path": spec.model_relative_path,
        "model_provenance_repository_relative_path": spec.model_manifest_relative_path,
        "qwen_matched_config": (
            "phase40-matched-qwen-controls-v1"
            if spec.model_family == "qwen"
            else None
        ),
        "full_optimizer_steps": 1245 if spec.model_family == "qwen" else 312,
        "gguf_export": (
            {
                "schema_version": "phase40-gguf-export-v1",
                "package_pin": GGUF_PACKAGE_PIN,
                "runtime_pin": LLAMA_CPP_PYTHON_PIN,
                "converter_sha256": GGUF_CONVERTER_SHA256,
                "outtype": "q8_0",
                "slug": spec.gguf_slug,
            }
            if spec.model_family == "qwen"
            else None
        ),
    }
    issues: list[NotebookValidationIssue] = []
    if set(phase) != set(expected):
        issues.append(
            _issue(
                path,
                "metadata-contract",
                "phase40 metadata fields must equal the canonical closed schema",
            )
        )
    for field, value in expected.items():
        if phase.get(field) != value:
            issues.append(_metadata_issue(path, field, phase.get(field), value))
    return issues


def _validate_ast(
    path: Path,
    sources: list[tuple[int, str, str]],
) -> list[NotebookValidationIssue]:
    issues: list[NotebookValidationIssue] = []
    repo_import_allowed = False
    forbidden_import_roots = {
        "anthropic",
        "datasets",
        "matplotlib",
        "numpy",
        "openai",
        "pandas",
        "requests",
        "seaborn",
        "sklearn",
    }
    forbidden_call_names = {
        "AutoModelForCausalLM",
        "AutoModelForSequenceClassification",
        "AutoTokenizer",
        "BitsAndBytesConfig",
        "DataCollatorWithPadding",
        "LoraConfig",
        "Trainer",
        "TrainingArguments",
        "compute_metrics",
        "get_peft_model",
        "load_dataset",
        "prepare_model_for_kbit_training",
        "snapshot_download",
    }
    for cell_index, role, source in sources:
        if role == "request-verify":
            repo_import_allowed = True
        try:
            tree = ast.parse(source, filename=f"{path.name}:cell-{cell_index}")
        except SyntaxError as exc:
            issues.append(
                _issue(
                    path,
                    "invalid-python",
                    f"code cell is not valid Python: {exc.msg}",
                    cell_index=cell_index,
                )
            )
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                roots = {alias.name.split(".", 1)[0] for alias in node.names}
                if roots & forbidden_import_roots:
                    issues.append(
                        _issue(
                            path,
                            "inline-implementation",
                            f"notebook imports forbidden implementation dependency {sorted(roots & forbidden_import_roots)!r}",
                            cell_index=cell_index,
                        )
                    )
                if "src" in roots and not repo_import_allowed:
                    issues.append(
                        _issue(
                            path,
                            "source-order",
                            "repository import occurs before source verification/extraction",
                            cell_index=cell_index,
                        )
                    )
            elif isinstance(node, ast.ImportFrom):
                root = (node.module or "").split(".", 1)[0]
                if root in forbidden_import_roots:
                    issues.append(
                        _issue(
                            path,
                            "inline-implementation",
                            f"notebook imports forbidden implementation dependency {root!r}",
                            cell_index=cell_index,
                        )
                    )
                if root == "src" and not repo_import_allowed:
                    issues.append(
                        _issue(
                            path,
                            "source-order",
                            "repository import occurs before source verification/extraction",
                            cell_index=cell_index,
                        )
                    )
            elif isinstance(node, ast.Call):
                function_name = ""
                if isinstance(node.func, ast.Name):
                    function_name = node.func.id
                elif isinstance(node.func, ast.Attribute):
                    function_name = node.func.attr
                if function_name in forbidden_call_names:
                    issues.append(
                        _issue(
                            path,
                            "inline-implementation",
                            f"notebook calls forbidden implementation primitive {function_name}",
                            cell_index=cell_index,
                        )
                    )
    return issues


def _validate_text_rules(
    path: Path,
    sources: list[tuple[int, str, str]],
) -> list[NotebookValidationIssue]:
    issues: list[NotebookValidationIssue] = []
    code = "\n".join(source for _, _, source in sources)
    lowered = code.casefold()
    scanned_code = code.replace(TORCH_INDEX_URL, "")
    forbidden_patterns = (
        ("stale-data-path", r"recovered[-_ ]balanced|data[\\/]splits"),
        ("personal-path", r"(?i)(?:[a-z]:[\\/]|onedrive|/users/|/home/|(?:^|[\s'\"])(?:~)[\\/])"),
        ("embedded-secret", r"(?i)(?:api[_-]?key|access[_-]?token|authorization|bearer|password|client[_-]?secret)\s*="),
        ("external-inference", r"(?i)(?:anthropic|openai|generativeai|inferenceclient|api\.openai|api\.anthropic|curl\s|wget\s|git\s+clone)"),
        ("broad-discovery", r"(?i)(?:\.r?glob\s*\(|os\.walk\s*\(|listdir\s*\(|\.iterdir\s*\()"),
        ("reserved-reader", r"(?i)(?:held[_-]?out|(?:^|[/\\'\"])(?:test|holdout)(?:\.jsonl|[/\\'\"]))"),
        ("implicit-mode", r"(?i)(?:--full-precision|use_4bit|infer(?:red)?[_-]?mode)"),
        ("probe-lineage", r"(?i)(?:--post-warmup-steps|--warmup-steps|--smoke-test|probe[_-]?adapter|probe[_-]?checkpoint|upload[_-]?adapter)"),
        ("inline-implementation", r"(?i)(?:confusion_matrix\s*\(|precision_recall_fscore_support\s*\(|plt\.|sns\.|trainer\s*=|compute_metrics\s*=|repair[_-]?output|fuzzy[_-]?label)"),
    )
    for code_name, pattern in forbidden_patterns:
        if re.search(pattern, scanned_code):
            issues.append(
                _issue(path, code_name, f"notebook source matches forbidden pattern {pattern!r}")
            )
    if any(operator in code for operator in (">=", "~=", "*")):
        # Multiplication is absent from the canonical controllers; treating '*'
        # as a pin wildcard makes dependency mutation fail closed.
        issues.append(
            _issue(path, "unpinned-dependency", "dependency/controller source contains a range or wildcard operator")
        )
    allowed_drive_fragments = (
        FIXED_TRANSFER_REPOSITORY_ROOT,
        FIXED_INPUT_DRIVE_PATH,
        "/content/drive/MyDrive/internship-phase40/work",
        "/content/drive/MyDrive/internship-phase40/exports",
    )
    for drive_path in re.findall(r"/content/drive[^\s'\"\)\]]+", code):
        if not any(drive_path.startswith(prefix) for prefix in allowed_drive_fragments):
            issues.append(
                _issue(path, "alternate-drive-path", f"non-canonical Drive path: {drive_path}")
            )
    if "phase40-input-manifest.json" not in code or "train.jsonl" not in code or "val.jsonl" not in code:
        issues.append(_issue(path, "input-members", "exact input member allowlist is absent"))
    if lowered.count("phase40-train-validation.zip") < 1:
        issues.append(_issue(path, "input-path", "fixed input archive path is absent"))
    if "src.model_adaptation.cli" in code:
        issues.append(
            _issue(
                path,
                "legacy-controller",
                "notebook must use the archive-closed Phase 40 operator module",
            )
        )
    return issues


def _validate_role_contracts(
    path: Path,
    role_sources: Mapping[str, tuple[int, str]],
    spec: _NotebookSpec,
) -> list[NotebookValidationIssue]:
    issues: list[NotebookValidationIssue] = []

    required_by_role: dict[str, tuple[str, ...]] = {
        "overview": (
            "STOP_PACKAGE_AUTHORITY",
            "model acquisition",
            "fresh full run",
        ),
        "constants": (
            FIXED_TRANSFER_REPOSITORY_ROOT,
            FIXED_SOURCE_ARCHIVE_PATH,
            FIXED_SOURCE_INVENTORY_PATH,
            FIXED_SOURCE_EXTRACTION_ROOT,
            FIXED_INPUT_DRIVE_PATH,
            FIXED_INPUT_EXTRACTION_ROOT,
            "phase40-input-manifest.json",
            "train.jsonl",
            "val.jsonl",
            spec.model_id,
            spec.model_revision,
            spec.model_family,
            spec.adaptation_mode,
            spec.model_relative_path,
            spec.model_manifest_relative_path,
            "RUN_KIND = \"full\"",
            "src.model_adaptation.phase40_operator",
            "FRESH_RUNTIME_REQUIRED = True",
            "FULL_OPTIMIZER_STEPS",
            TORCH_INDEX_URL,
        ),
        "drive-mount": ("from google.colab import drive", "drive.mount(\"/content/drive\")"),
        "package-authority": (
            "PACKAGE_AUTHORITY_GRANTED = False",
            "MODEL_ACQUISITION_AUTHORIZED = False",
            "STOP_PACKAGE_AUTHORITY",
            "is not True",
            "FRESH_RUNTIME_REQUIRED",
        ),
        "source-verify": (
            "SOURCE_BUNDLE_VERIFIED = False",
            "repository_relative_archive_path",
            "repository_relative_inventory_path",
            "archive_sha256",
            "inventory_sha256",
            "SOURCE_ARCHIVE_RELATIVE",
            "SOURCE_INVENTORY_RELATIVE",
            "hashlib.sha256",
            "zipfile.ZipFile",
            "io.BytesIO(source_archive_bytes)",
            "source_inventory_payload[\"archive_sha256\"]",
            "SOURCE_BUNDLE_VERIFIED = True",
        ),
        "source-extract": (
            "if SOURCE_BUNDLE_VERIFIED is not True",
            "SOURCE_EXTRACTION_ROOT",
            "verified_source_payloads",
            "write_bytes",
            "sys.path.insert",
        ),
        "package-install": (
            "if PACKAGE_AUTHORITY_GRANTED is not True",
            "pip",
            "install",
            "PACKAGE_INSTALL_PINS",
            "DEPENDENCY_PINS",
            "MODE_NO_DEPS_PINS",
            "TORCH_INDEX_URL",
        ),
        "request-verify": (
            "from src.model_adaptation.phase40_handoff import RunRequest",
            "verify_phase40_run_request",
            "verify_input=False",
            "step_origin != 0",
            "probe_parent is not None",
            "control_template_by_run",
            'CONTROL_VALUES.get("model_id")',
            "source_bundle",
            "input_bundle",
            "verify_launch_ready_request",
            "max_optimizer_steps",
            "FULL_OPTIMIZER_STEPS",
            "OPERATOR_LOG_ROOT",
            "subprocess.Popen",
        ),
        "model-acquire": (
            "phase40-acquire-model",
            "--authorize-model-acquisition",
            "--run-id",
            "MODEL_ACQUISITION_AUTHORIZED",
            "BASE_MODEL_PATH",
            "BASE_MODEL_MANIFEST_PATH",
            "MODEL_SNAPSHOT_VERIFIED = True",
        ),
        "input-verify": (
            "phase40-verify-input-bundle",
            "--archive-path",
            "--reference-path",
            "--extraction-root",
            "input_authority.archive_sha256",
            "input_authority.manifest_sha256",
            "data_member.ordered_row_ids_sha256",
            "snapshot_row_id_version",
            "INPUT_MEMBERS",
            "INPUT_BUNDLE_VERIFIED = True",
        ),
        "doctor": (
            "phase40-doctor",
            "--model-family",
            "--adaptation-mode",
            "--run-kind",
            "--model-revision",
            "--run-request-path",
            "--input-root",
            "--base-model-path",
            "--base-model-manifest-path",
        ),
        "resume-policy": (
            "EXACT_RESUME_CHECKPOINT = None",
            "phase40-verify-resume",
            "EXACT_RESUME_VERIFIED",
            "--base-model-path",
            "--base-model-manifest-path",
        ),
        "full-run": (
            f'\"{spec.run_command}\"',
            "--run-id",
            "--request-path",
            "--input-archive",
            "--extraction-root",
            "--repo-root",
            "--output-root",
            "MODEL_ACQUISITION_AUTHORIZED",
            "MODEL_SNAPSHOT_VERIFIED",
            "INPUT_BUNDLE_VERIFIED",
            "EXACT_RESUME_VERIFIED",
            "--base-model-path",
            "--base-model-manifest-path",
            "--resume-from-checkpoint",
        ),
        "evidence-verify": (
            "phase40-verify-run-evidence",
            "--run-root",
        ),
        "graph-regenerate": (
            "phase40-render-graphs",
            "--run-root",
            "phase40-verify-run-evidence",
        ),
        "bundle-export": (
            "RETURNED_BUNDLE_ROOT",
            "phase40-verify-run-evidence",
            "Verified request-bound bundle ready for unchanged return",
        ),
    }
    if spec.filename == "qwen_lora_colab.ipynb":
        required_by_role["request-verify"] += (
            "OPERATOR_LOG_ROOT_PREEXISTED",
            "OPERATOR_LOG_ATTEMPT_ROOT",
            "uuid.uuid4().hex",
            "OPERATOR_LOG_ATTEMPT_ROOT.mkdir(parents=False, exist_ok=False)",
            'log_path = OPERATOR_LOG_ATTEMPT_ROOT /',
            'log_path.open("x"',
        )
        required_by_role["resume-policy"] += (
            "OPERATOR_LOG_ROOT_PREEXISTED",
            "automatic or latest resume is forbidden",
            "exact resume requires the original append-only operator-log root",
            "Path(EXACT_RESUME_CHECKPOINT)",
            "is_absolute",
        )
    if spec.model_family == "phobert":
        required_by_role["full-run"] += ("classification-head",)
    else:
        required_by_role["full-run"] += (
            "phase40-train-qwen",
            "--adaptation-mode",
            spec.adaptation_mode,
        )
        required_by_role["gguf-authority"] = (
            GGUF_PACKAGE_PIN,
            "GGUF_CONVERTER_SHA256",
            "package_metadata.distribution",
            "convert_hf_to_gguf.py",
            "GGUF_CONVERTER_VERIFIED = True",
        )
        required_by_role["gguf-export"] = (
            "GGUF_CLI",
            "export",
            "--run-root",
            "--base-model-path",
            "--base-manifest-path",
            "--converter-script",
            "--converter-sha256",
            "--output-path",
            "--manifest-path",
            "--temp-parent",
            "verify",
            "phase40-gguf-export-v1",
            "output_claim.get(\"path\"",
            "output_claim.get(\"sha256\")",
            "GGUF_OUTPUT_PATH.resolve(strict=True)",
            "GGUF_MANIFEST_VERIFIED = True",
            "GGUF_DRIVE_ROOT",
        )
        required_by_role["optional-download"] = (
            "ENABLE_BROWSER_DOWNLOAD = False",
            "GGUF_MANIFEST_VERIFIED is not True",
            "from google.colab import files",
            "files.download",
        )

    for role, tokens in required_by_role.items():
        cell_index, source = role_sources[role]
        issues.extend(
            _require_tokens(
                path=path,
                source=source,
                role=role,
                cell_index=cell_index,
                tokens=tokens,
            )
        )

    constants_source = role_sources["constants"][1]
    for pin in spec.dependency_pins:
        if pin not in constants_source:
            issues.append(
                _issue(path, "unpinned-dependency", f"missing exact dependency pin {pin!r}")
            )
    other_mode_pin = PHOBERT_ONLY_PIN if spec.model_family == "qwen" else QLORA_ONLY_PIN
    if other_mode_pin in constants_source:
        issues.append(
            _issue(path, "mode-package-drift", f"unrelated mode-only package appears: {other_mode_pin}")
        )
    if spec.adaptation_mode == "lora" and QLORA_ONLY_PIN in constants_source:
        issues.append(_issue(path, "mode-package-drift", "LoRA notebook includes bitsandbytes"))
    if (
        "DEPENDENCY_PINS[1:]" in constants_source
        or "tuple(pin for pin in DEPENDENCY_PINS if pin not in MODE_NO_DEPS_PINS)"
        not in constants_source
    ):
        issues.append(
            _issue(
                path,
                "torch-install",
                "package installation must include the exact Torch pin and exclude only explicit no-deps mode pins",
                cell_index=role_sources["constants"][0],
            )
        )
    if "install_command.extend(PACKAGE_INSTALL_PINS)" not in role_sources["package-install"][1]:
        issues.append(
            _issue(
                path,
                "torch-install",
                "package installation does not consume the complete install pin set",
                cell_index=role_sources["package-install"][0],
            )
        )

    # Ordering checks are intentionally role-aware instead of relying on the
    # textual claim made by a markdown cell.
    input_verify_index = role_sources["input-verify"][0]
    source_verify_index = role_sources["source-verify"][0]
    source_extract_index = role_sources["source-extract"][0]
    if not source_verify_index < source_extract_index:
        issues.append(_issue(path, "source-order", "source extraction precedes verification"))
    if source_extract_index >= input_verify_index:
        # Source extraction must happen before importing the verifier; input
        # verification itself still precedes every data access.
        issues.append(_issue(path, "source-order", "source activation order is not canonical"))
    for role, (cell_index, source) in role_sources.items():
        if cell_index >= input_verify_index:
            continue
        compact = re.sub(r"\s+", " ", source.casefold())
        if re.search(
            r"(?:open|read_text|read_bytes|load_dataset)\s*\([^\n]*(?:train\.jsonl|val\.jsonl|input_extraction_root)",
            compact,
        ):
            issues.append(
                _issue(
                    path,
                    "input-order",
                    "input member access occurs before automated bundle verification",
                    cell_index=cell_index,
                )
            )
        if "input_extraction_root.mkdir" in compact or "input_archive_path.extract" in compact:
            issues.append(
                _issue(
                    path,
                    "input-order",
                    "input extraction occurs before automated bundle verification",
                    cell_index=cell_index,
                )
            )
    return issues


def validate_phase40_notebook(path: Path) -> tuple[NotebookValidationIssue, ...]:
    """Parse and statically validate one canonical Phase 40 notebook.

    Validation is read-only and performs no notebook execution, imports from
    notebook code, package installation, network access, or data access.
    """

    path = Path(path)
    spec = _SPECS.get(path.name)
    if spec is None:
        return (_issue(path, "unexpected-notebook", "not a canonical Phase 40 notebook name"),)
    if path.is_symlink():
        return (_issue(path, "unsafe-notebook", "notebook path must not be a symbolic link"),)
    try:
        payload = path.read_bytes()
    except FileNotFoundError:
        return (_issue(path, "missing-notebook", "canonical notebook is missing"),)
    try:
        text = payload.decode("utf-8", errors="strict")
        notebook = json.loads(text, object_pairs_hook=_reject_duplicate_keys)
    except (UnicodeDecodeError, json.JSONDecodeError, _DuplicateJsonKey) as exc:
        return (_issue(path, "invalid-notebook-json", str(exc)),)
    if not isinstance(notebook, dict):
        return (_issue(path, "invalid-notebook-json", "notebook root must be an object"),)

    issues: list[NotebookValidationIssue] = []
    if notebook.get("nbformat") != 4 or not isinstance(notebook.get("nbformat_minor"), int):
        issues.append(_issue(path, "notebook-format", "notebook must use nbformat 4"))
    metadata = notebook.get("metadata")
    phase = metadata.get("phase40") if isinstance(metadata, dict) else None
    issues.extend(_validate_phase_metadata(path, phase, spec))

    cells = notebook.get("cells")
    if not isinstance(cells, list):
        return tuple(issues + [_issue(path, "cell-layout", "cells must be a list")])
    actual_layout: list[tuple[object, object]] = []
    role_sources: dict[str, tuple[int, str]] = {}
    code_sources: list[tuple[int, str, str]] = []
    for index, cell in enumerate(cells):
        if not isinstance(cell, dict):
            issues.append(_issue(path, "cell-layout", "cell must be an object", cell_index=index))
            continue
        cell_metadata = cell.get("metadata")
        role = cell_metadata.get("phase40_role") if isinstance(cell_metadata, dict) else None
        cell_type = cell.get("cell_type")
        actual_layout.append((role, cell_type))
        try:
            source = _source_text(cell)
        except ValueError as exc:
            issues.append(_issue(path, "cell-source", str(exc), cell_index=index))
            continue
        if isinstance(role, str):
            if role in role_sources:
                issues.append(_issue(path, "cell-layout", f"duplicate role {role!r}", cell_index=index))
            else:
                role_sources[role] = (index, source)
        if cell_type == "code":
            if cell.get("execution_count") is not None or cell.get("outputs") != []:
                issues.append(
                    _issue(
                        path,
                        "executed-notebook",
                        "canonical controller must have no execution count or retained outputs",
                        cell_index=index,
                    )
                )
            code_sources.append((index, str(role), source))
    expected_layout = _ROLE_LAYOUT + (_QWEN_GGUF_ROLE_LAYOUT if spec.model_family == "qwen" else ())
    if tuple(actual_layout) != expected_layout:
        issues.append(
            _issue(path, "cell-layout", "cell roles/types must equal the canonical closed layout")
        )
    if set(role_sources) != {role for role, _ in expected_layout}:
        issues.append(_issue(path, "cell-layout", "canonical role set is incomplete or extended"))
        return tuple(issues)

    issues.extend(_validate_ast(path, code_sources))
    issues.extend(_validate_text_rules(path, code_sources))
    issues.extend(_validate_role_contracts(path, role_sources, spec))
    try:
        source_digest = _normalized_source_sha256(notebook)
    except ValueError as exc:
        issues.append(_issue(path, "cell-source", str(exc)))
    else:
        if source_digest != _CANONICAL_SOURCE_DIGESTS[path.name]:
            issues.append(
                _issue(
                    path,
                    "controller-source-drift",
                    "normalized controller source differs from the reviewed canonical artifact",
                )
            )
    return tuple(issues)


def validate_phase40_notebooks(root: Path) -> tuple[NotebookValidationIssue, ...]:
    """Validate the exact three-notebook Phase 40 directory."""

    root = Path(root)
    issues: list[NotebookValidationIssue] = []
    if not root.exists() or not root.is_dir() or root.is_symlink():
        return (_issue(root, "notebook-root", "notebook root must be a real directory"),)
    actual = tuple(sorted(path.name for path in root.glob("*.ipynb")))
    expected = tuple(sorted(_SPECS))
    if actual != expected:
        issues.append(
            _issue(
                root,
                "notebook-set",
                f"notebook directory must contain exactly {expected!r}; got {actual!r}",
            )
        )
    for filename in expected:
        issues.extend(validate_phase40_notebook(root / filename))
    return tuple(issues)


def notebook_source_sha256(path: Path) -> str:
    """Return a normalized source-only digest useful in audit reports."""

    notebook = json.loads(Path(path).read_text(encoding="utf-8", errors="strict"))
    return _normalized_source_sha256(notebook)


__all__ = [
    "NotebookValidationIssue",
    "notebook_source_sha256",
    "validate_phase40_notebook",
    "validate_phase40_notebooks",
]
