"""Frozen, model-specific inference contracts for Phase 41.

This module deliberately contains no transformers, torch, PEFT, filesystem-model
loader, or dataset import.  Phase 40 must construct and smoke-test the concrete
adapters before the irreversible evaluator is entered.  Phase 41 receives only
immutable protocol authorities and already-loaded callables.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import re
from types import MappingProxyType
from typing import Callable, Mapping, Sequence, TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover - import cycle guard for type checkers
    from src.model_adaptation.phase41_evaluation import InMemorySnapshot, Prediction


SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
PROTOCOL_NAME = "frozen-inference-protocols.json"
PROTOCOL_SCHEMA_VERSION = "phase41-frozen-inference-protocols-v2"


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
            raise ProtocolContractError(
                f"{self.role} protocol fields differ from the frozen contract"
            )
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
    "bundle_root_sha256",
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
    "quantization",
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
    "bundle_root_sha256",
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
_QWEN_RUNTIME_PACKAGES = frozenset(
    {"torch", "transformers", "peft", "bitsandbytes", "huggingface-hub"}
)
_PHOBERT_RUNTIME_PACKAGES = frozenset(
    {"torch", "transformers", "underthesea", "huggingface-hub"}
)
_QWEN_QUANTIZATION_FIELDS = {
    "load_in_4bit",
    "bnb_4bit_compute_dtype",
    "bnb_4bit_quant_type",
    "bnb_4bit_use_double_quant",
    "device_map",
    "low_cpu_mem_usage",
}
_QWEN_DECODER = {
    "do_sample": False,
    "num_return_sequences": 1,
    "temperature": 0.0,
    "top_p": 1.0,
    "max_new_tokens": 256,
}


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
        if not isinstance(decoder, dict) or set(decoder) != set(_QWEN_DECODER):
            raise ProtocolContractError("Qwen decoder controls are incomplete")
        if decoder != _QWEN_DECODER:
            raise ProtocolContractError("Qwen decoder controls drifted from Phase 40")
        quantization = body["quantization"]
        if not isinstance(quantization, dict) or set(quantization) != _QWEN_QUANTIZATION_FIELDS:
            raise ProtocolContractError("Qwen QLoRA quantization controls are incomplete")
        if (
            quantization["load_in_4bit"] is not True
            or quantization["bnb_4bit_quant_type"] != "nf4"
            or quantization["bnb_4bit_use_double_quant"] is not True
            or quantization["bnb_4bit_compute_dtype"] not in {"float16", "bfloat16"}
            or quantization["device_map"] != {"": 0}
            or quantization["low_cpu_mem_usage"] is not True
        ):
            raise ProtocolContractError("Qwen must reproduce the frozen NF4 QLoRA load contract")
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
    python_identity = runtime["python"]
    device = runtime["device"]
    if python_identity == "synthetic":
        expected = (
            {"fake"}
            if role == "qwen"
            else {"fake", "underthesea"}
        )
        if set(packages) != expected or device != "cpu-fake":
            raise ProtocolContractError(f"{role} synthetic runtime identity drifted")
    else:
        expected = _QWEN_RUNTIME_PACKAGES if role == "qwen" else _PHOBERT_RUNTIME_PACKAGES
        if (
            not isinstance(python_identity, str)
            or not re.fullmatch(r"\d+\.\d+\.\d+", python_identity)
            or set(packages) != expected
            or any(not isinstance(version, str) or not version for version in packages.values())
            or not isinstance(device, str)
            or not re.fullmatch(r"cuda:\d+", device)
        ):
            raise ProtocolContractError(f"{role} production runtime identity drifted")
        if role == "qwen" and packages["bitsandbytes"] != "0.50.1":
            raise ProtocolContractError("Qwen bitsandbytes version drifted")
        if role == "phobert" and packages["underthesea"] != body["segmenter_version"]:
            raise ProtocolContractError("PhoBERT segmenter package/version drifted")
    smoke = body["synthetic_smoke"]
    if not isinstance(smoke, dict) or set(smoke) != {"input_sha256", "expected_state"}:
        raise ProtocolContractError(f"{role} synthetic smoke authority is incomplete")
    _require_sha(smoke["input_sha256"], f"{role}.synthetic_smoke.input_sha256")
    if smoke["expected_state"] not in _LABELS:
        raise ProtocolContractError(f"{role} synthetic smoke state is invalid")
    _require_sha(body["bundle_root_sha256"], f"{role}.bundle_root_sha256")
    bundle_root = Path(str(body["bundle_root"]))
    if body["runtime"]["python"] == "synthetic":
        if (
            not isinstance(body["bundle_root"], str)
            or not body["bundle_root"]
            or bundle_root.is_absolute()
            or ".." in bundle_root.parts
        ):
            raise ProtocolContractError(
                f"{role}.bundle_root must be a safe synthetic relative path"
            )
    elif (
        not isinstance(body["bundle_root"], str)
        or not body["bundle_root"]
        or not bundle_root.is_absolute()
        or ".." in bundle_root.parts
        or bundle_root.parent == bundle_root
    ):
        raise ProtocolContractError(
            f"{role}.bundle_root must be an absolute non-root immutable bundle path"
        )
    for key in ("model_artifact_relative_path", "tokenizer_artifact_relative_path"):
        value = body[key]
        if (
            not isinstance(value, str)
            or not value
            or Path(value).is_absolute()
            or ".." in Path(value).parts
        ):
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
            "schema_version": PROTOCOL_SCHEMA_VERSION,
            "models": [self.qwen.as_dict(), self.phobert.as_dict()],
        }

    def as_dict(self) -> dict[str, object]:
        body = self._body_without_hash()
        body["authority_sha256"] = self.authority_sha256
        return body


def _tree_inventory(root: Path) -> tuple[tuple[str, str, int], ...]:
    """Inventory one non-redirecting tree without accepting special entries."""

    path = Path(root)
    if not path.is_absolute() or not path.is_dir() or _path_is_redirecting(path):
        raise ProtocolContractError("immutable model root is absent or redirecting")
    rows: list[tuple[str, str, int]] = [(".", "directory", 0)]
    try:
        entries = tuple(path.rglob("*"))
        for entry in entries:
            if _path_is_redirecting(entry):
                raise ProtocolContractError(
                    "immutable model tree contains a redirecting entry"
                )
            relative = entry.relative_to(path).as_posix()
            if entry.is_dir():
                rows.append((relative, "directory", 0))
            elif entry.is_file():
                rows.append((relative, "file", entry.stat().st_size))
            else:
                raise ProtocolContractError(
                    "immutable model tree contains a special filesystem entry"
                )
    except OSError as exc:
        raise ProtocolContractError("immutable model tree inventory failed") from exc
    return tuple(sorted(rows))


class _ImmutableTreeLease:
    """Lifetime lock for exact Windows model bytes plus a closed inventory."""

    __slots__ = (
        "root",
        "description",
        "_inventory",
        "_handles",
        "_identity_sha256",
        "_closed",
        "_changed",
        "_watch_kernel32",
        "_watch_handle",
        "_watch_event",
        "_watch_buffer",
        "_watch_bytes",
        "_watch_overlapped",
        "_handle_kernel32",
        "_handle_info_type",
    )

    def __init__(
        self,
        root: Path,
        *,
        description: str,
        checksum_builder: Callable[[Path], str] | None = None,
        expected_sha256: str | None = None,
    ) -> None:
        if os.name != "nt":
            raise ProtocolContractError(
                "production model lifetime locks require Windows share-mode enforcement"
            )
        self.root = Path(root)
        self.description = description
        if not self.root.is_absolute() or self.root.parent == self.root:
            raise ProtocolContractError(f"{description} root must be absolute and bounded")
        self._inventory: tuple[tuple[str, str, int], ...] = ()
        self._handles: list[object] = []
        self._identity_sha256: str | None = None
        self._closed = False
        self._changed = False
        self._watch_kernel32 = None
        self._watch_handle = None
        self._watch_event = None
        self._watch_buffer = None
        self._watch_bytes = None
        self._watch_overlapped = None
        self._handle_kernel32 = None
        self._handle_info_type = None
        try:
            self._configure_windows_handle_api()
            self._acquire_ancestor_handles()
            self._inventory = _tree_inventory(self.root)
            self._acquire_windows_handles()
            self._start_windows_change_fence()
            if _tree_inventory(self.root) != self._inventory:
                raise ProtocolContractError(
                    f"{description} changed while lifetime locks were acquired"
                )
            if expected_sha256 is not None:
                expected = _require_sha(expected_sha256, f"{description} identity")
                if checksum_builder is None or checksum_builder(self.root) != expected:
                    raise ProtocolContractError(f"{description} identity drifted")
                self._identity_sha256 = expected
            self.assert_intact()
        except BaseException:
            self.close()
            raise

    def _configure_windows_handle_api(self) -> None:
        import ctypes
        from ctypes import wintypes

        class FileTime(ctypes.Structure):
            _fields_ = [
                ("dwLowDateTime", wintypes.DWORD),
                ("dwHighDateTime", wintypes.DWORD),
            ]

        class ByHandleFileInformation(ctypes.Structure):
            _fields_ = [
                ("dwFileAttributes", wintypes.DWORD),
                ("ftCreationTime", FileTime),
                ("ftLastAccessTime", FileTime),
                ("ftLastWriteTime", FileTime),
                ("dwVolumeSerialNumber", wintypes.DWORD),
                ("nFileSizeHigh", wintypes.DWORD),
                ("nFileSizeLow", wintypes.DWORD),
                ("nNumberOfLinks", wintypes.DWORD),
                ("nFileIndexHigh", wintypes.DWORD),
                ("nFileIndexLow", wintypes.DWORD),
            ]

        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.CreateFileW.argtypes = [
            wintypes.LPCWSTR,
            wintypes.DWORD,
            wintypes.DWORD,
            wintypes.LPVOID,
            wintypes.DWORD,
            wintypes.DWORD,
            wintypes.HANDLE,
        ]
        kernel32.CreateFileW.restype = wintypes.HANDLE
        kernel32.GetFileInformationByHandle.argtypes = [
            wintypes.HANDLE,
            ctypes.POINTER(ByHandleFileInformation),
        ]
        kernel32.GetFileInformationByHandle.restype = wintypes.BOOL
        kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
        kernel32.CloseHandle.restype = wintypes.BOOL
        self._handle_kernel32 = kernel32
        self._handle_info_type = ByHandleFileInformation

    def _open_locked_path(
        self,
        target: Path,
        *,
        deny_write: bool,
    ) -> object:
        import ctypes

        if self._handle_kernel32 is None or self._handle_info_type is None:
            raise ProtocolContractError(
                f"{self.description} Windows handle API is unavailable"
            )
        kernel32 = self._handle_kernel32
        invalid = ctypes.c_void_p(-1).value
        # GENERIC_READ is required even for ancestry handles.  A handle opened
        # with FILE_READ_ATTRIBUTES alone does not deny a direct directory
        # rename on current Windows, despite omitting FILE_SHARE_DELETE.
        desired_access = 0x80000000
        share_mode = 0x00000001 if deny_write else 0x00000003
        handle = kernel32.CreateFileW(
            str(target),
            desired_access,  # sealed bytes are readable; ancestors need attributes
            share_mode,  # always deny delete; sealed entries also deny write
            None,
            3,  # OPEN_EXISTING
            0x00200000 | 0x02000000,  # OPEN_REPARSE_POINT | BACKUP_SEMANTICS
            None,
        )
        if handle == invalid:
            code = ctypes.get_last_error()
            raise ProtocolContractError(
                f"{self.description} could not lock path ancestry/tree: "
                f"winerror={code}"
            )
        self._handles.append((kernel32, handle))
        return handle

    def _validate_locked_path(
        self,
        handle: object,
        *,
        expected_directory: bool,
    ) -> None:
        import ctypes

        if self._handle_kernel32 is None or self._handle_info_type is None:
            raise ProtocolContractError(
                f"{self.description} Windows handle API is unavailable"
            )
        kernel32 = self._handle_kernel32
        information = self._handle_info_type()
        if not kernel32.GetFileInformationByHandle(handle, ctypes.byref(information)):
            code = ctypes.get_last_error()
            raise ProtocolContractError(
                f"{self.description} could not inspect a held path: winerror={code}"
            )
        attributes = int(information.dwFileAttributes)
        is_directory = bool(attributes & 0x00000010)
        if attributes & 0x00000400 or is_directory is not expected_directory:
            raise ProtocolContractError(
                f"{self.description} held path is reparse-pointed or type-drifted"
            )

    def _acquire_ancestor_handles(self) -> None:
        held_ancestors = []
        for ancestor in reversed((self.root, *self.root.parents)):
            handle = self._open_locked_path(
                ancestor,
                deny_write=False,
            )
            held_ancestors.append(handle)
        for handle in held_ancestors:
            self._validate_locked_path(
                handle,
                expected_directory=True,
            )

    def _acquire_windows_handles(self) -> None:
        for relative, kind, _ in self._inventory:
            target = self.root if relative == "." else self.root / relative
            handle = self._open_locked_path(
                target,
                deny_write=True,
            )
            self._validate_locked_path(
                handle,
                expected_directory=kind == "directory",
            )

    def _start_windows_change_fence(self) -> None:
        import ctypes
        from ctypes import wintypes

        class Overlapped(ctypes.Structure):
            _fields_ = [
                ("Internal", ctypes.c_size_t),
                ("InternalHigh", ctypes.c_size_t),
                ("Offset", wintypes.DWORD),
                ("OffsetHigh", wintypes.DWORD),
                ("hEvent", wintypes.HANDLE),
            ]

        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.CreateFileW.argtypes = [
            wintypes.LPCWSTR,
            wintypes.DWORD,
            wintypes.DWORD,
            wintypes.LPVOID,
            wintypes.DWORD,
            wintypes.DWORD,
            wintypes.HANDLE,
        ]
        kernel32.CreateFileW.restype = wintypes.HANDLE
        kernel32.CreateEventW.argtypes = [
            wintypes.LPVOID,
            wintypes.BOOL,
            wintypes.BOOL,
            wintypes.LPCWSTR,
        ]
        kernel32.CreateEventW.restype = wintypes.HANDLE
        kernel32.ReadDirectoryChangesW.argtypes = [
            wintypes.HANDLE,
            wintypes.LPVOID,
            wintypes.DWORD,
            wintypes.BOOL,
            wintypes.DWORD,
            wintypes.LPVOID,
            ctypes.POINTER(Overlapped),
            wintypes.LPVOID,
        ]
        kernel32.ReadDirectoryChangesW.restype = wintypes.BOOL
        kernel32.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
        kernel32.WaitForSingleObject.restype = wintypes.DWORD
        kernel32.CancelIoEx.argtypes = [wintypes.HANDLE, ctypes.POINTER(Overlapped)]
        kernel32.CancelIoEx.restype = wintypes.BOOL
        kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
        kernel32.CloseHandle.restype = wintypes.BOOL
        invalid = ctypes.c_void_p(-1).value
        watch_handle = kernel32.CreateFileW(
            str(self.root),
            0x00000001,  # FILE_LIST_DIRECTORY
            0x00000007,  # share read/write/delete; the watcher records mutation
            None,
            3,  # OPEN_EXISTING
            0x02000000 | 0x40000000,  # BACKUP_SEMANTICS | OVERLAPPED
            None,
        )
        if watch_handle == invalid:
            raise ProtocolContractError(
                f"{self.description} could not open its directory-change fence"
            )
        event = kernel32.CreateEventW(None, True, False, None)
        if not event:
            kernel32.CloseHandle(watch_handle)
            raise ProtocolContractError(
                f"{self.description} could not create its directory-change event"
            )
        buffer = ctypes.create_string_buffer(65536)
        returned = wintypes.DWORD(0)
        overlapped = Overlapped()
        overlapped.hEvent = event
        queued = kernel32.ReadDirectoryChangesW(
            watch_handle,
            buffer,
            len(buffer),
            True,
            0x0000015F,  # names, attributes, size, writes, creation, security
            ctypes.byref(returned),
            ctypes.byref(overlapped),
            None,
        )
        if not queued and ctypes.get_last_error() != 997:  # ERROR_IO_PENDING
            kernel32.CloseHandle(event)
            kernel32.CloseHandle(watch_handle)
            raise ProtocolContractError(
                f"{self.description} could not arm its directory-change fence"
            )
        self._watch_kernel32 = kernel32
        self._watch_handle = watch_handle
        self._watch_event = event
        self._watch_buffer = buffer
        self._watch_bytes = returned
        self._watch_overlapped = overlapped

    def _assert_change_fence_clean(self) -> None:
        if (
            self._watch_kernel32 is None
            or self._watch_handle is None
            or self._watch_event is None
        ):
            raise ProtocolContractError(
                f"{self.description} directory-change fence is unavailable"
            )
        status = self._watch_kernel32.WaitForSingleObject(self._watch_event, 0)
        if status == 0:  # WAIT_OBJECT_0
            self._changed = True
        elif status != 258:  # WAIT_TIMEOUT
            raise ProtocolContractError(
                f"{self.description} directory-change fence failed"
            )
        if self._changed:
            raise ProtocolContractError(
                f"{self.description} changed during its lifetime lease"
            )

    @property
    def identity_sha256(self) -> str:
        if self._identity_sha256 is None:
            raise ProtocolContractError(
                f"{self.description} has no bound semantic identity"
            )
        return self._identity_sha256

    def bind_semantic_identity(self, identity_sha256: str) -> None:
        identity = _require_sha(identity_sha256, f"{self.description} identity")
        if self._identity_sha256 not in {None, identity}:
            raise ProtocolContractError(f"{self.description} identity was rebound")
        self._identity_sha256 = identity
        self.assert_intact()

    def assert_intact(self) -> None:
        expected_handles = len((self.root, *self.root.parents)) + len(self._inventory)
        if (
            self._closed
            or not self._inventory
            or not self._handles
            or len(self._handles) != expected_handles
        ):
            raise ProtocolContractError(f"{self.description} lifetime lease is closed")
        for record in self._handles:
            if (
                not isinstance(record, tuple)
                or len(record) != 2
                or record[0] is not self._handle_kernel32
                or not record[1]
            ):
                raise ProtocolContractError(
                    f"{self.description} lifetime lease lacks live OS handles"
                )
        self._assert_change_fence_clean()
        if _tree_inventory(self.root) != self._inventory:
            raise ProtocolContractError(
                f"{self.description} inventory changed during its lifetime lease"
            )

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        if (
            self._watch_kernel32 is not None
            and self._watch_handle is not None
            and self._watch_overlapped is not None
        ):
            import ctypes

            self._watch_kernel32.CancelIoEx(
                self._watch_handle,
                ctypes.byref(self._watch_overlapped),
            )
        if self._watch_kernel32 is not None and self._watch_event is not None:
            self._watch_kernel32.CloseHandle(self._watch_event)
        if self._watch_kernel32 is not None and self._watch_handle is not None:
            self._watch_kernel32.CloseHandle(self._watch_handle)
        self._watch_event = None
        self._watch_handle = None
        while self._handles:
            kernel32, handle = self._handles.pop()
            kernel32.CloseHandle(handle)

    def __del__(self) -> None:  # pragma: no cover - process-exit safety net
        try:
            self.close()
        except Exception:
            pass


def _run_with_immutable_leases(
    leases: Sequence[_ImmutableTreeLease], action: Callable[[], object]
) -> object:
    for lease in leases:
        lease.assert_intact()
    try:
        result = action()
    except BaseException as exc:
        try:
            for lease in leases:
                lease.assert_intact()
        except BaseException as integrity_exc:
            raise integrity_exc from exc
        raise
    for lease in leases:
        lease.assert_intact()
    return result


PredictorCallable = Callable[["InMemorySnapshot"], Sequence["Prediction"]]


def _lexical_path_key(path: Path) -> str:
    return os.path.normcase(os.path.abspath(os.path.normpath(os.fspath(path))))


def _assert_loaded_predictor_state(
    value: object,
    *,
    role: str,
    expected_binding: object | None = None,
) -> str:
    """Prove live model leases and the OS-backed launcher binding at use time."""

    protocol = getattr(value, "protocol", None)
    if type(protocol) is not FrozenInferenceProtocol or protocol.role != role:
        raise ProtocolContractError(f"{role} production predictor protocol is invalid")
    if (
        getattr(value, "loaded", None) is not True
        or getattr(value, "smoke_verified", None) is not True
    ):
        raise ProtocolContractError(
            f"{role} production predictor was not loaded and smoke-verified"
        )
    leases = getattr(value, "_leases", None)
    if (
        type(leases) is not tuple
        or len(leases) != 2
        or leases[0] is leases[1]
        or any(type(lease) is not _ImmutableTreeLease for lease in leases)
    ):
        raise ProtocolContractError(
            f"{role} production predictor requires exactly two live model leases"
        )
    try:
        for lease in leases:
            lease.assert_intact()
        lease_identities = tuple(lease.identity_sha256 for lease in leases)
    except Exception as exc:
        raise ProtocolContractError(
            f"{role} production predictor lacks live OS-backed model leases"
        ) from exc
    expected_identities = (
        _require_sha(protocol.body["bundle_root_sha256"], f"{role} bundle identity"),
        _require_sha(protocol.body["base_snapshot_sha256"], f"{role} base identity"),
    )
    if lease_identities != expected_identities:
        raise ProtocolContractError(f"{role} production lease identities drifted")
    expected_bundle_root = Path(str(protocol.body["bundle_root"]))
    if _lexical_path_key(leases[0].root) != _lexical_path_key(expected_bundle_root):
        raise ProtocolContractError(f"{role} production bundle lease root drifted")
    authority_sha256 = _require_sha(
        getattr(value, "_authority_sha256", None),
        f"{role} protocol authority identity",
    )
    output_root = getattr(value, "_output_root", None)
    if not isinstance(output_root, Path) or not output_root.is_absolute():
        raise ProtocolContractError(f"{role} production output root is invalid")
    try:
        durable_authority = load_protocol_authority(output_root)
    except Exception as exc:
        raise ProtocolContractError(
            f"{role} durable protocol authority is unavailable"
        ) from exc
    durable_protocol = (
        durable_authority.qwen if role == "qwen" else durable_authority.phobert
    )
    if (
        durable_authority.authority_sha256 != authority_sha256
        or durable_protocol.protocol_sha256 != protocol.protocol_sha256
    ):
        raise ProtocolContractError(f"{role} durable protocol authority drifted")
    launcher_binding = getattr(value, "_launcher_binding", None)
    if launcher_binding is None or (
        expected_binding is not None and launcher_binding is not expected_binding
    ):
        raise ProtocolContractError(f"{role} launcher binding drifted")
    capability_sha256 = _require_sha(
        getattr(value, "_launcher_capability_sha256", None),
        f"{role} launcher capability",
    )
    try:
        from src.model_adaptation.phase41_evaluation import (
            _require_live_launcher_capability,
        )

        observed_binding = _require_live_launcher_capability(
            output_root,
            consume=False,
        )
    except Exception as exc:
        raise ProtocolContractError(
            f"{role} launcher binding is not OS-verified and live"
        ) from exc
    if (
        observed_binding is None
        or observed_binding is not launcher_binding
        or getattr(observed_binding, "launcher_capability_sha256", None)
        != capability_sha256
    ):
        raise ProtocolContractError(f"{role} launcher binding is not live and exact")
    return capability_sha256


@dataclass(frozen=True, slots=True, init=False)
class FrozenQwenPredictor:
    protocol: FrozenInferenceProtocol
    predictor: PredictorCallable
    loaded: bool
    smoke_verified: bool
    _leases: tuple[_ImmutableTreeLease, ...] = field(repr=False, compare=False)
    _authority_sha256: str | None = field(repr=False, compare=False)
    _output_root: Path | None = field(repr=False, compare=False)
    _launcher_binding: object | None = field(repr=False, compare=False)
    _launcher_capability_sha256: str | None = field(repr=False, compare=False)

    def __init__(
        self,
        protocol: FrozenInferenceProtocol,
        predictor: PredictorCallable,
    ) -> None:
        """Construct only a synthetic test double; production uses the private factory."""

        if protocol.role != "qwen" or not callable(predictor):
            raise ProtocolContractError("Qwen predictor must be callable and protocol-bound")
        if protocol.body["runtime"]["python"] != "synthetic":
            raise ProtocolContractError(
                "Qwen public predictor construction is synthetic test-only"
            )
        object.__setattr__(self, "protocol", protocol)
        object.__setattr__(self, "predictor", predictor)
        object.__setattr__(self, "loaded", False)
        object.__setattr__(self, "smoke_verified", False)
        object.__setattr__(self, "_leases", ())
        object.__setattr__(self, "_authority_sha256", None)
        object.__setattr__(self, "_output_root", None)
        object.__setattr__(self, "_launcher_binding", None)
        object.__setattr__(self, "_launcher_capability_sha256", None)

    @property
    def production_verified(self) -> bool:
        if self.loaded is not True or self.smoke_verified is not True:
            return False
        try:
            _assert_loaded_predictor_state(self, role="qwen")
        except Exception:
            return False
        return True

    @property
    def launcher_capability_sha256(self) -> str | None:
        try:
            return _assert_loaded_predictor_state(self, role="qwen")
        except Exception:
            return None

    @property
    def synthetic_test_only(self) -> bool:
        return self.protocol.body["runtime"]["python"] == "synthetic"

    def _has_launcher_binding(self, binding: object) -> bool:
        try:
            _assert_loaded_predictor_state(
                self,
                role="qwen",
                expected_binding=binding,
            )
        except Exception:
            return False
        return True

    def assert_lifetime_integrity(self) -> None:
        _assert_loaded_predictor_state(self, role="qwen")

    def __call__(self, snapshot: "InMemorySnapshot") -> Sequence["Prediction"]:
        if not self.synthetic_test_only:
            self.assert_lifetime_integrity()
        return self.predictor(snapshot)


@dataclass(frozen=True, slots=True, init=False)
class FrozenPhoBertPredictor:
    protocol: FrozenInferenceProtocol
    predictor: PredictorCallable
    loaded: bool
    smoke_verified: bool
    _leases: tuple[_ImmutableTreeLease, ...] = field(repr=False, compare=False)
    _authority_sha256: str | None = field(repr=False, compare=False)
    _output_root: Path | None = field(repr=False, compare=False)
    _launcher_binding: object | None = field(repr=False, compare=False)
    _launcher_capability_sha256: str | None = field(repr=False, compare=False)

    def __init__(
        self,
        protocol: FrozenInferenceProtocol,
        predictor: PredictorCallable,
    ) -> None:
        """Construct only a synthetic test double; production uses the private factory."""

        if protocol.role != "phobert" or not callable(predictor):
            raise ProtocolContractError("PhoBERT predictor must be callable and protocol-bound")
        if protocol.body["runtime"]["python"] != "synthetic":
            raise ProtocolContractError(
                "PhoBERT public predictor construction is synthetic test-only"
            )
        object.__setattr__(self, "protocol", protocol)
        object.__setattr__(self, "predictor", predictor)
        object.__setattr__(self, "loaded", False)
        object.__setattr__(self, "smoke_verified", False)
        object.__setattr__(self, "_leases", ())
        object.__setattr__(self, "_authority_sha256", None)
        object.__setattr__(self, "_output_root", None)
        object.__setattr__(self, "_launcher_binding", None)
        object.__setattr__(self, "_launcher_capability_sha256", None)

    @property
    def production_verified(self) -> bool:
        if self.loaded is not True or self.smoke_verified is not True:
            return False
        try:
            _assert_loaded_predictor_state(self, role="phobert")
        except Exception:
            return False
        return True

    @property
    def launcher_capability_sha256(self) -> str | None:
        try:
            return _assert_loaded_predictor_state(self, role="phobert")
        except Exception:
            return None

    @property
    def synthetic_test_only(self) -> bool:
        return self.protocol.body["runtime"]["python"] == "synthetic"

    def _has_launcher_binding(self, binding: object) -> bool:
        try:
            _assert_loaded_predictor_state(
                self,
                role="phobert",
                expected_binding=binding,
            )
        except Exception:
            return False
        return True

    def assert_lifetime_integrity(self) -> None:
        _assert_loaded_predictor_state(self, role="phobert")

    def __call__(self, snapshot: "InMemorySnapshot") -> Sequence["Prediction"]:
        if not self.synthetic_test_only:
            self.assert_lifetime_integrity()
        return self.predictor(snapshot)


def _protocol(role: str, body: dict[str, object]) -> FrozenInferenceProtocol:
    return FrozenInferenceProtocol(role, body, _sha256(canonical_json_bytes(body)))


def build_protocol_authority(
    qwen_body: Mapping[str, object], phobert_body: Mapping[str, object]
) -> Phase41ProtocolAuthority:
    qwen = _protocol("qwen", dict(qwen_body))
    phobert = _protocol("phobert", dict(phobert_body))
    body = {
        "schema_version": PROTOCOL_SCHEMA_VERSION,
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
        "bundle_root_sha256": "8" * 64,
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
        "quantization": {
            "load_in_4bit": True,
            "bnb_4bit_compute_dtype": "float16",
            "bnb_4bit_quant_type": "nf4",
            "bnb_4bit_use_double_quant": True,
            "device_map": {"": 0},
            "low_cpu_mem_usage": True,
        },
        "decoder": dict(_QWEN_DECODER),
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
        "bundle_root_sha256": "7" * 64,
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
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_BINARY", 0)
    descriptor = os.open(path, flags, 0o600)
    try:
        with os.fdopen(descriptor, "wb", closefd=False) as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
    finally:
        os.close(descriptor)
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
    if raw["schema_version"] != PROTOCOL_SCHEMA_VERSION or payload != canonical_json_bytes(raw):
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


def _path_is_redirecting(path: Path) -> bool:
    if path.is_symlink():
        return True
    is_junction = getattr(path, "is_junction", None)
    if callable(is_junction) and is_junction():
        return True
    try:
        attributes = getattr(path.stat(follow_symlinks=False), "st_file_attributes", 0)
    except OSError:
        return False
    return bool(attributes & 0x00000400)  # FILE_ATTRIBUTE_REPARSE_POINT


def _bound_bundle_root(
    protocol: FrozenInferenceProtocol,
    *,
    checksum_builder: Callable[[Path], str],
) -> _ImmutableTreeLease:
    """Verify one absolute, separately sealed model bundle before any import/load."""

    if protocol.body["runtime"]["python"] == "synthetic":
        raise ProtocolContractError(
            f"{protocol.role} synthetic protocol cannot enter the production loader"
        )
    root = Path(str(protocol.body["bundle_root"]))
    if not root.is_absolute() or root.parent == root:
        raise ProtocolContractError(f"{protocol.role} bundle root is not absolute and bounded")
    if not root.is_dir() or any(_path_is_redirecting(part) for part in (root, *root.parents)):
        raise ProtocolContractError(f"{protocol.role} bundle root is absent or redirecting")
    return _ImmutableTreeLease(
        root,
        description=f"{protocol.role} immutable bundle",
        checksum_builder=checksum_builder,
        expected_sha256=str(protocol.body["bundle_root_sha256"]),
    )


def _build_qwen_qlora_loader_kwargs(
    protocol: FrozenInferenceProtocol,
    *,
    transformers_module: object,
    torch_module: object,
) -> dict[str, object]:
    """Reproduce the exact Phase 40 NF4 base-load call from frozen fields."""

    if protocol.role != "qwen":
        raise ProtocolContractError("QLoRA loader controls require the Qwen protocol")
    frozen = dict(protocol.body["quantization"])
    dtype_name = str(frozen["bnb_4bit_compute_dtype"])
    compute_dtype = getattr(torch_module, dtype_name, None)
    config_type = getattr(transformers_module, "BitsAndBytesConfig", None)
    if compute_dtype is None or config_type is None or not callable(config_type):
        raise ProtocolContractError("Qwen frozen BitsAndBytesConfig runtime is unavailable")
    quantization_config = config_type(
        load_in_4bit=frozen["load_in_4bit"],
        bnb_4bit_compute_dtype=compute_dtype,
        bnb_4bit_quant_type=frozen["bnb_4bit_quant_type"],
        bnb_4bit_use_double_quant=frozen["bnb_4bit_use_double_quant"],
    )
    observed = {
        "load_in_4bit": getattr(quantization_config, "load_in_4bit", None),
        "bnb_4bit_compute_dtype": getattr(
            quantization_config, "bnb_4bit_compute_dtype", None
        ),
        "bnb_4bit_quant_type": getattr(
            quantization_config, "bnb_4bit_quant_type", None
        ),
        "bnb_4bit_use_double_quant": getattr(
            quantization_config, "bnb_4bit_use_double_quant", None
        ),
    }
    expected = {
        "load_in_4bit": True,
        "bnb_4bit_compute_dtype": compute_dtype,
        "bnb_4bit_quant_type": "nf4",
        "bnb_4bit_use_double_quant": True,
    }
    if observed != expected:
        raise ProtocolContractError("Qwen BitsAndBytesConfig construction drifted")
    return {
        "revision": str(protocol.body["base_revision"]),
        "local_files_only": True,
        "trust_remote_code": False,
        "low_cpu_mem_usage": frozen["low_cpu_mem_usage"],
        "quantization_config": quantization_config,
        "device_map": dict(frozen["device_map"]),
    }


def _qwen_generation_controls(protocol: FrozenInferenceProtocol) -> dict[str, object]:
    if protocol.role != "qwen":
        raise ProtocolContractError("Qwen generation controls require the Qwen protocol")
    controls = dict(protocol.body["decoder"])
    if controls != _QWEN_DECODER:
        raise ProtocolContractError("Qwen generation controls drifted after protocol freeze")
    return controls


def _load_phase41_production_predictors_impl(
    output_root: Path,
) -> tuple[FrozenQwenPredictor, FrozenPhoBertPredictor]:
    """Load and smoke the two code-fixed local artifacts without a data opener.

    Heavy libraries are imported only inside this run-only function, so prepare
    and verify-only commands cannot allocate GPU memory or load a model.
    """

    from src.model_adaptation.phase41_evaluation import (
        _load_materialization_receipt,
        _require_live_launcher_capability,
    )
    from src.model_adaptation.registry import build_model_checksum

    root = Path(output_root)
    authority = load_protocol_authority(root)
    launcher_binding = _require_live_launcher_capability(root, consume=False)
    materialization = _load_materialization_receipt(root)
    if launcher_binding is None or materialization is None:
        raise ProtocolContractError("production loader lacks a live launcher capability")
    launcher_capability_sha256 = materialization[0].get(
        "launcher_capability_sha256"
    )
    launcher_capability_sha256 = _require_sha(
        launcher_capability_sha256, "live launcher capability"
    )
    bundle_leases = {
        protocol.role: _bound_bundle_root(
            protocol,
            checksum_builder=build_model_checksum,
        )
        for protocol in (authority.qwen, authority.phobert)
    }

    def artifact(protocol: FrozenInferenceProtocol, key: str, expected_sha: str) -> Path:
        lease = bundle_leases[protocol.role]
        lease.assert_intact()
        bundle = lease.root
        relative = Path(str(protocol.body[key]))
        target = bundle / relative
        if not target.exists() or _path_is_redirecting(target):
            raise ProtocolContractError(f"{protocol.role} bound artifact is absent: {key}")
        if build_model_checksum(target) != expected_sha:
            raise ProtocolContractError(f"{protocol.role} bound artifact hash drifted: {key}")
        lease.assert_intact()
        return target

    def verify_packages(protocol: FrozenInferenceProtocol) -> None:
        runtime = protocol.body["runtime"]
        assert isinstance(runtime, Mapping)
        expected_python = runtime["python"]
        if platform.python_version() != expected_python:
            raise ProtocolContractError(
                f"{protocol.role} Python runtime drifted"
            )
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
        import bitsandbytes
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
            BitsAndBytesConfig,
        )
        from peft import PeftModel
        from underthesea import word_tokenize
    except ImportError as exc:  # pragma: no cover - depends on run-only environment
        raise ProtocolContractError("Phase 41 model runtime dependencies are unavailable") from exc

    def frozen_cuda_device(protocol: FrozenInferenceProtocol):  # noqa: ANN202
        identity = str(protocol.body["runtime"]["device"])
        if not torch.cuda.is_available():
            raise ProtocolContractError(
                f"{protocol.role} frozen CUDA device is unavailable"
            )
        index = int(identity.removeprefix("cuda:"))
        if index < 0 or index >= torch.cuda.device_count():
            raise ProtocolContractError(
                f"{protocol.role} frozen CUDA device is unavailable: {identity}"
            )
        return torch.device(identity), index

    qwen_device, qwen_device_index = frozen_cuda_device(authority.qwen)
    phobert_device, _ = frozen_cuda_device(authority.phobert)

    qwen_base_root = Path(
        _run_with_immutable_leases(
            (bundle_leases["qwen"],),
            lambda: snapshot_download(
                repo_id=str(authority.qwen.body["base_model_id"]),
                revision=str(authority.qwen.body["base_revision"]),
                local_files_only=True,
            ),
        )
    )
    qwen_base_lease = _ImmutableTreeLease(
        qwen_base_root,
        description="Qwen base snapshot",
    )
    qwen_base = _run_with_immutable_leases(
        (bundle_leases["qwen"], qwen_base_lease),
        lambda: verify_qwen_base_model_provenance(
            qwen_base_root,
            qwen_model_root / PHASE40_BASE_MODEL_MANIFEST_NAME,
            model_id=str(authority.qwen.body["base_model_id"]),
            model_revision=str(authority.qwen.body["base_revision"]),
        ),
    )
    if qwen_base.snapshot_content_sha256 != authority.qwen.body["base_snapshot_sha256"]:
        raise ProtocolContractError("Qwen base snapshot identity drifted")
    qwen_base_lease.bind_semantic_identity(
        str(authority.qwen.body["base_snapshot_sha256"])
    )
    phobert_base_root = Path(
        _run_with_immutable_leases(
            (bundle_leases["phobert"],),
            lambda: snapshot_download(
                repo_id=str(authority.phobert.body["base_model_id"]),
                revision=str(authority.phobert.body["base_revision"]),
                local_files_only=True,
            ),
        )
    )
    phobert_base_lease = _ImmutableTreeLease(
        phobert_base_root,
        description="PhoBERT base snapshot",
    )
    phobert_base = _run_with_immutable_leases(
        (bundle_leases["phobert"], phobert_base_lease),
        lambda: verify_phobert_base_model_provenance(
            phobert_base_root,
            phobert_model_root / PHOBERT_BASE_MODEL_MANIFEST_NAME,
        ),
    )
    if (
        phobert_base.snapshot_content_sha256
        != authority.phobert.body["base_snapshot_sha256"]
        or authority.phobert.body["preprocessor_sha256"]
        != PHOBERT_PREPROCESSOR_SHA256
    ):
        raise ProtocolContractError("PhoBERT base/preprocessor identity drifted")
    phobert_base_lease.bind_semantic_identity(
        str(authority.phobert.body["base_snapshot_sha256"])
    )

    qwen_leases = (bundle_leases["qwen"], qwen_base_lease)
    phobert_leases = (bundle_leases["phobert"], phobert_base_lease)
    qwen_tokenizer = _run_with_immutable_leases(
        qwen_leases,
        lambda: AutoTokenizer.from_pretrained(
            qwen_tokenizer_root,
            local_files_only=True,
            trust_remote_code=False,
        ),
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
    qwen_base = _run_with_immutable_leases(
        qwen_leases,
        lambda: AutoModelForCausalLM.from_pretrained(
            qwen_base_root,
            **_build_qwen_qlora_loader_kwargs(
                authority.qwen,
                transformers_module=type(
                    "_TransformersBindings",
                    (),
                    {"BitsAndBytesConfig": BitsAndBytesConfig},
                ),
                torch_module=torch,
            ),
        ),
    )
    linear4bit_type = getattr(getattr(bitsandbytes, "nn", None), "Linear4bit", None)
    quantized_layers = (
        sum(1 for module in qwen_base.modules() if isinstance(module, linear4bit_type))
        if isinstance(linear4bit_type, type)
        else 0
    )
    device_map = getattr(qwen_base, "hf_device_map", None)
    if (
        getattr(qwen_base, "is_loaded_in_4bit", False) is not True
        or quantized_layers <= 0
        or not isinstance(device_map, Mapping)
        or set(device_map) != {""}
        or str(device_map[""]) not in {str(qwen_device_index), str(qwen_device)}
    ):
        raise ProtocolContractError(
            "Qwen runtime did not reproduce genuine single-device NF4 loading"
        )
    qwen_model = _run_with_immutable_leases(
        qwen_leases,
        lambda: PeftModel.from_pretrained(
            qwen_base,
            qwen_model_root,
            is_trainable=False,
        ),
    )
    if next(qwen_model.parameters()).device != qwen_device:
        raise ProtocolContractError("Qwen model did not load on the frozen CUDA device")
    qwen_model.eval()

    phobert_tokenizer = _run_with_immutable_leases(
        phobert_leases,
        lambda: AutoTokenizer.from_pretrained(
            phobert_tokenizer_root,
            local_files_only=True,
            trust_remote_code=False,
        ),
    )
    phobert_model = _run_with_immutable_leases(
        phobert_leases,
        lambda: AutoModelForSequenceClassification.from_pretrained(
            phobert_model_root,
            local_files_only=True,
            trust_remote_code=False,
        ),
    )
    phobert_model.to(phobert_device)
    if next(phobert_model.parameters()).device != phobert_device:
        raise ProtocolContractError("PhoBERT model did not load on the frozen CUDA device")
    phobert_model.eval()

    from src.model_adaptation.phase41_evaluation import (
        InMemorySnapshot,
        InferenceRow,
        Prediction,
    )

    def qwen_predict_unlocked(snapshot: InMemorySnapshot):  # noqa: ANN202
        predictions = []
        template = json.loads(str(authority.qwen.body["prompt_template"]))
        generation_controls = _qwen_generation_controls(authority.qwen)
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
            if input_length > int(authority.qwen.body["max_sequence_length"]):
                predictions.append(
                    Prediction(
                        row.row_id,
                        "invalid_output",
                        "",
                        "qwen_input_exceeds_frozen_max_sequence_length",
                    )
                )
                continue
            with torch.inference_mode():
                output = qwen_model.generate(**encoded, **generation_controls)
            raw = qwen_tokenizer.decode(output[0][input_length:], skip_special_tokens=True)
            parsed = parse_qwen_prediction(raw)
            state = parsed.state.value
            error = "invalid_qwen_output" if state == "invalid_output" else None
            predictions.append(Prediction(row.row_id, state, raw, error))
        return tuple(predictions)

    def qwen_predict(snapshot: InMemorySnapshot):  # noqa: ANN202
        return _run_with_immutable_leases(
            qwen_leases,
            lambda: qwen_predict_unlocked(snapshot),
        )

    def phobert_predict_unlocked(snapshot: InMemorySnapshot):  # noqa: ANN202
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
        if tuple(logits.shape) != (len(snapshot.rows), 4) or not torch.isfinite(
            logits
        ).all().item():
            raise ProtocolContractError("PhoBERT logits differ from the frozen four-logit contract")
        indices = torch.argmax(logits, dim=-1).tolist()
        return tuple(
            Prediction(row.row_id, str(index_map[str(index)]), str(index_map[str(index)]), None)
            for row, index in zip(snapshot.rows, indices, strict=True)
        )

    def phobert_predict(snapshot: InMemorySnapshot):  # noqa: ANN202
        return _run_with_immutable_leases(
            phobert_leases,
            lambda: phobert_predict_unlocked(snapshot),
        )

    smoke_text = "tin nhắn tổng hợp"
    smoke = InMemorySnapshot((InferenceRow("phase41-smoke", 0, smoke_text),))
    for protocol, predictor in (
        (authority.qwen, qwen_predict),
        (authority.phobert, phobert_predict),
    ):
        expected_hash = protocol.body["synthetic_smoke"]["input_sha256"]
        if _sha256(smoke_text.encode("utf-8")) != expected_hash:
            raise ProtocolContractError(f"{protocol.role} synthetic smoke input drifted")
        predictions = tuple(predictor(smoke))
        expected_state = protocol.body["synthetic_smoke"]["expected_state"]
        if len(predictions) != 1 or predictions[0].predicted_state != expected_state:
            raise ProtocolContractError(f"{protocol.role} synthetic smoke output drifted")
    live_binding_after_smoke = _require_live_launcher_capability(root, consume=False)
    if live_binding_after_smoke is not launcher_binding:
        raise ProtocolContractError("launcher capability changed during model load/smoke")
    for lease in (*qwen_leases, *phobert_leases):
        lease.assert_intact()

    qwen = object.__new__(FrozenQwenPredictor)
    object.__setattr__(qwen, "protocol", authority.qwen)
    object.__setattr__(qwen, "predictor", qwen_predict)
    object.__setattr__(qwen, "loaded", True)
    object.__setattr__(qwen, "smoke_verified", True)
    object.__setattr__(qwen, "_leases", qwen_leases)
    object.__setattr__(qwen, "_authority_sha256", authority.authority_sha256)
    object.__setattr__(qwen, "_output_root", root.absolute())
    object.__setattr__(qwen, "_launcher_binding", launcher_binding)
    object.__setattr__(
        qwen,
        "_launcher_capability_sha256",
        launcher_capability_sha256,
    )
    phobert = object.__new__(FrozenPhoBertPredictor)
    object.__setattr__(phobert, "protocol", authority.phobert)
    object.__setattr__(phobert, "predictor", phobert_predict)
    object.__setattr__(phobert, "loaded", True)
    object.__setattr__(phobert, "smoke_verified", True)
    object.__setattr__(phobert, "_leases", phobert_leases)
    object.__setattr__(phobert, "_authority_sha256", authority.authority_sha256)
    object.__setattr__(phobert, "_output_root", root.absolute())
    object.__setattr__(phobert, "_launcher_binding", launcher_binding)
    object.__setattr__(
        phobert,
        "_launcher_capability_sha256",
        launcher_capability_sha256,
    )
    qwen.assert_lifetime_integrity()
    phobert.assert_lifetime_integrity()
    return qwen, phobert


load_phase41_production_predictors = _load_phase41_production_predictors_impl


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
