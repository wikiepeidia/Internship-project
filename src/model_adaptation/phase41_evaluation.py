"""Fail-closed, one-shot two-model evaluation for the Phase 41 holdout.

Preparation treats the held-out identity as opaque metadata.  Only
``run_phase41_once`` is allowed to acquire the payload, and it durably spends
the content identity before doing so.  The production entry owns model loading
and accepts no predictor, opener, or capability supplied by its caller.
"""

from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from datetime import datetime, timezone
import ast
import hashlib
import json
import marshal
import math
import ntpath
import os
from pathlib import Path
import platform
import re
import subprocess
import sys
import sysconfig
from types import CodeType, ModuleType
from typing import BinaryIO, Callable, Iterable, Iterator, Mapping, Sequence
import uuid


LABEL_ORDER = (
    "bank_impersonation",
    "zalo_social_engineering",
    "task_scam",
    "benign",
)
RISKY_LABELS = LABEL_ORDER[:3]
PREDICTION_COLUMNS = LABEL_ORDER + ("invalid_output",)
DATASET_KEYS = frozenset(
    {
        "text",
        "label",
        "risk_tier",
        "suspicious_spans",
        "xai_explanation",
        "source",
        "seed_id",
    }
)
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
SAFE_ID_RE = re.compile(r"^[a-z0-9][a-z0-9._-]{0,95}$")
SAFE_PARSER_ERROR_RE = re.compile(r"^[a-z0-9][a-z0-9_]{0,63}$")
DEFERRED_AUTHORIZATION_SIGNAL = (
    "AUTHORIZE PHASE 41 ONE-SHOT; DEPLOYMENT FIT DEFERRED"
)
AUTHORIZED_POST_EVALUATION_FIT_SIGNAL = (
    "AUTHORIZE PHASE 41 ONE-SHOT; SEPARATE DEPLOYMENT FIT AUTHORIZED"
)
_AUTHORIZATION_SIGNAL_CHOICES = {
    DEFERRED_AUTHORIZATION_SIGNAL: "deferred",
    AUTHORIZED_POST_EVALUATION_FIT_SIGNAL: "authorized_post_evaluation_fit",
}

PREPARED_NAME = "evaluation-request.json"
AUTHORIZATION_NAME = "one-shot-authorization.json"
CLAIM_NAME = "one-shot-claim.json"
QWEN_PREDICTIONS_NAME = "qwen-predictions.jsonl"
PHOBERT_PREDICTIONS_NAME = "phobert-predictions.jsonl"
RESULTS_NAME = "results.json"
REPORT_NAME = "results.md"
TERMINAL_NAME = "terminal.json"
PREAUTHORIZATION_NAME = "preauthorization-receipt.json"
PROTOCOLS_NAME = "frozen-inference-protocols.json"
SOURCE_MANIFEST_NAME = "execution-source-manifest.json"
ACCESS_RECEIPT_NAME = "evaluation-access-receipt.json"
EVIDENCE_MANIFEST_NAME = "evidence-manifest.json"
DEPLOYMENT_DISPOSITION_NAME = "deployment-fit-disposition.json"
PENDING_DEPLOYMENT_FIT_CHOICE = "pending_human_authorization"
MATERIALIZATION_RECEIPT_NAME = "execution-materialization-receipt.json"
COMPLETION_SEAL_NAME = "protected-completion-seal.json"
PHASE41_PRODUCTION_BOOTSTRAP_REQUIRED = (
    "phase41_production_runtime_source_bootstrap_required"
)
PRODUCTION_PREPARATION_SCOPE = "production_canonical"
SYNTHETIC_PREPARATION_SCOPE = "synthetic_test"
_PHASE40_REQUIRED_AUTHORITY_HASH_FIELDS = (
    "qwen_gguf_verification_receipt_sha256",
    "phobert_release_receipt_authority_sha256",
    "phobert_segmenter_authority_sha256",
    "runtime_dependency_authority_sha256",
    "runtime_materialization_receipt_sha256",
)
_PRODUCTION_EXTRA_AUTHORITY_HASH_FIELDS = (
    "phase39_contract_file_sha256",
    "phase39_data_contract_sha256",
    "scope_amendment_sha256",
    "superseded_scope_amendment_sha256",
    "final_comparison_authority_sha256",
    "comparison_finalizer_source_sha256",
    "claim_registry_authority_sha256",
    "model_smokes_sha256",
)
_PRIOR_HUMAN_EXPOSURE_DISCLOSURE = (
    "Held-out message content had prior human exposure during corpus-quality "
    "review and thesis drafting; Phase 41 remains a one-shot model evaluation, "
    "not a claim of untouched human blinding."
)
_TERMINAL_PREAUTHORIZATION_POLICY = {
    "model_selection_after_test": False,
    "tuning_after_test": False,
    "dataset_repair_after_test": False,
    "retry_after_claim": False,
    "post_test_contingency_activation": False,
}
_SYNTHETIC_REQUIRED_AUTHORITY_HASHES = {
    name: hashlib.sha256(f"phase41-synthetic:{name}".encode("ascii")).hexdigest()
    for name in _PHASE40_REQUIRED_AUTHORITY_HASH_FIELDS
}

_PHASE39_AUTHORITY_RELATIVE = Path(
    ".planning/phases/39-independent-quality-re-judge/"
    "39-DOWNSTREAM-DATA-CONTRACT.json"
)
_PHASE40_COMPARISON_RELATIVE = Path("data/models/phase40/comparison-manifest.json")
_PHASE40_REVIEW_RELATIVE = Path(
    "data/models/phase40/review/human-review-manifest.json"
)
_PHASE40_RETURNED_ROOTS = (
    "data/models/phase40/full/qwen-qlora",
    "data/models/phase40/full/phobert",
)
_PHASE41_ENTRY_MODULES = (
    "src.model_adaptation.cli",
    "src.model_adaptation.phase41_evaluation",
    "src.model_adaptation.phase41_protocols",
)
EVIDENCE_ARTIFACT_NAMES = (
    PREPARED_NAME,
    PROTOCOLS_NAME,
    SOURCE_MANIFEST_NAME,
    MATERIALIZATION_RECEIPT_NAME,
    PREAUTHORIZATION_NAME,
    AUTHORIZATION_NAME,
    CLAIM_NAME,
    ACCESS_RECEIPT_NAME,
    QWEN_PREDICTIONS_NAME,
    PHOBERT_PREDICTIONS_NAME,
    RESULTS_NAME,
    REPORT_NAME,
)
_PRECLAIM_OUTPUT_NAMES = (
    CLAIM_NAME,
    ACCESS_RECEIPT_NAME,
    QWEN_PREDICTIONS_NAME,
    PHOBERT_PREDICTIONS_NAME,
    RESULTS_NAME,
    REPORT_NAME,
    EVIDENCE_MANIFEST_NAME,
    COMPLETION_SEAL_NAME,
    TERMINAL_NAME,
    DEPLOYMENT_DISPOSITION_NAME,
)

# One code-fixed, repository-local registry prevents replay when the same
# frozen bytes are copied to another path or evaluated under another output
# root in this checkout. Production must put the same SHA-keyed claim in
# protected persistence outside a mutable/copyable checkout. The public API
# intentionally does not accept a registry override.


@dataclass(frozen=True, slots=True)
class _TestRuntime:
    registry_root: Path
    event_sink: list[str] | None = None


_TEST_RUNTIME: ContextVar[_TestRuntime | None] = ContextVar(
    "phase41_test_runtime", default=None
)


@dataclass(frozen=True, slots=True)
class _AccessMetadata:
    requested_path_sha256: str
    final_path_sha256: str
    volume_serial_number: int
    file_identity: str


_ACCESS_METADATA: ContextVar[_AccessMetadata | None] = ContextVar(
    "phase41_access_metadata", default=None
)


@dataclass(slots=True)
class _LiveLauncherCapability:
    """OS-backed launcher lifetime proof created only from inherited stdin."""

    output_root_sha256: str
    pipe_handle: int
    launcher_process_handle: int
    launcher_process_id: int
    launcher_capability_sha256: str
    launcher_process_image_path_sha256: str
    launcher_process_image_sha256: str
    consumed: bool = False
    closed: bool = False

    def assert_live(self) -> None:
        if self.closed or os.name != "nt":
            raise ContractError("live inherited launcher capability is unavailable")
        import ctypes
        from ctypes import wintypes

        FILE_TYPE_PIPE = 3
        WAIT_TIMEOUT = 0x102
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        get_file_type = kernel32.GetFileType
        get_file_type.argtypes = [wintypes.HANDLE]
        get_file_type.restype = wintypes.DWORD
        if int(get_file_type(wintypes.HANDLE(self.pipe_handle))) != FILE_TYPE_PIPE:
            raise ContractError("inherited launcher capability is not a pipe")
        available = wintypes.DWORD()
        peek_pipe = kernel32.PeekNamedPipe
        peek_pipe.argtypes = [
            wintypes.HANDLE,
            ctypes.c_void_p,
            wintypes.DWORD,
            ctypes.POINTER(wintypes.DWORD),
            ctypes.POINTER(wintypes.DWORD),
            ctypes.POINTER(wintypes.DWORD),
        ]
        peek_pipe.restype = wintypes.BOOL
        if not peek_pipe(
            wintypes.HANDLE(self.pipe_handle),
            None,
            0,
            None,
            ctypes.byref(available),
            None,
        ) or available.value != 0:
            raise ContractError("launcher pipe is closed or contains extra bytes")
        wait_for_single_object = kernel32.WaitForSingleObject
        wait_for_single_object.argtypes = [wintypes.HANDLE, wintypes.DWORD]
        wait_for_single_object.restype = wintypes.DWORD
        if int(
            wait_for_single_object(
                wintypes.HANDLE(self.launcher_process_handle), 0
            )
        ) != WAIT_TIMEOUT:
            raise ContractError("launcher parent process is no longer live")

    def consume_once(self) -> None:
        self.assert_live()
        if self.consumed:
            raise ContractError("launcher capability was already consumed")
        self.consumed = True

    def close(self) -> None:
        if self.closed:
            return
        self.closed = True
        if os.name == "nt" and self.launcher_process_handle:
            import ctypes
            from ctypes import wintypes

            close_handle = ctypes.WinDLL(
                "kernel32", use_last_error=True
            ).CloseHandle
            close_handle.argtypes = [wintypes.HANDLE]
            close_handle.restype = wintypes.BOOL
            close_handle(wintypes.HANDLE(self.launcher_process_handle))


_LIVE_LAUNCHER_CAPABILITY: ContextVar[_LiveLauncherCapability | None] = ContextVar(
    "phase41_live_launcher_capability", default=None
)


@contextmanager
def _phase41_test_runtime(
    *, registry_root: Path, event_sink: list[str] | None = None
) -> Iterator[None]:
    """Private synthetic seam; production APIs expose no registry/opener override."""

    synthetic_registry = Path(registry_root)
    synthetic_registry.mkdir(parents=True, exist_ok=True)
    token = _TEST_RUNTIME.set(_TestRuntime(synthetic_registry, event_sink))
    try:
        yield
    finally:
        _TEST_RUNTIME.reset(token)


def _emit_test_event(name: str) -> None:
    runtime = _TEST_RUNTIME.get()
    if runtime is not None and runtime.event_sink is not None:
        runtime.event_sink.append(name)


def _claim_registry_root() -> Path:
    runtime = _TEST_RUNTIME.get()
    if runtime is not None:
        return runtime.registry_root
    return _known_program_data_root() / "VNPhish" / "phase41-one-shot-claims"


def _known_program_data_root() -> Path:
    """Resolve CommonApplicationData from the Windows Known Folder API.

    Environment variables are intentionally ignored: a mutable ``ProgramData``
    value cannot redirect the machine-global one-shot registry.
    """

    if os.name != "nt":
        raise ContractError("Phase 41 production access requires Windows")
    import ctypes
    from ctypes import wintypes

    class GUID(ctypes.Structure):
        _fields_ = [
            ("Data1", wintypes.DWORD),
            ("Data2", wintypes.WORD),
            ("Data3", wintypes.WORD),
            ("Data4", ctypes.c_ubyte * 8),
        ]

    folder_id = GUID.from_buffer_copy(
        uuid.UUID("62ab5d82-fdc1-4dc3-a9dd-070d1d495d97").bytes_le
    )
    resolved = wintypes.LPWSTR()
    shell32 = ctypes.WinDLL("shell32", use_last_error=True)
    ole32 = ctypes.WinDLL("ole32", use_last_error=True)
    shell32.SHGetKnownFolderPath.argtypes = [
        ctypes.POINTER(GUID),
        wintypes.DWORD,
        wintypes.HANDLE,
        ctypes.POINTER(wintypes.LPWSTR),
    ]
    shell32.SHGetKnownFolderPath.restype = ctypes.c_long
    ole32.CoTaskMemFree.argtypes = [ctypes.c_void_p]
    ole32.CoTaskMemFree.restype = None
    status = int(
        shell32.SHGetKnownFolderPath(
            ctypes.byref(folder_id), 0, None, ctypes.byref(resolved)
        )
    )
    if status != 0 or not resolved.value:
        raise ContractError("Windows CommonApplicationData identity is unavailable")
    try:
        value = resolved.value
    finally:
        ole32.CoTaskMemFree(ctypes.cast(resolved, ctypes.c_void_p))
    normalized = ntpath.normpath(value)
    if not ntpath.isabs(normalized) or ntpath.splitdrive(normalized)[0] == "":
        raise ContractError("Windows CommonApplicationData identity is unsafe")
    return Path(normalized)


def _windows_file_attributes(path: Path) -> int:
    if os.name != "nt":
        raise ContractError("Phase 41 production access requires Windows")
    import ctypes

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    get_attributes = kernel32.GetFileAttributesW
    get_attributes.argtypes = [ctypes.c_wchar_p]
    get_attributes.restype = ctypes.c_uint32
    attributes = int(get_attributes(os.fspath(path)))
    if attributes == 0xFFFFFFFF:
        code = ctypes.get_last_error()
        raise ContractError(f"unsafe reserved path: Win32 attributes unavailable ({code})")
    return attributes


@dataclass(frozen=True, slots=True)
class _RegistryAce:
    sid: str
    mask: int
    allowed: bool
    inherited: bool


def _validate_registry_acl_snapshot(
    *, owner_sid: str, dacl_protected: bool, aces: Sequence[_RegistryAce], operator_sid: str
) -> None:
    allowed_writers = {operator_sid, "S-1-5-18", "S-1-5-32-544"}
    # Directory create/write/delete plus ownership/DACL and generic write/all.
    write_control_mask = (
        0x00000002
        | 0x00000004
        | 0x00000010
        | 0x00000040
        | 0x00000100
        | 0x00010000
        | 0x00040000
        | 0x00080000
        | 0x10000000
        | 0x40000000
    )
    if not dacl_protected:
        raise ContractError("Phase 41 claim-registry DACL must be protected")
    if owner_sid not in allowed_writers:
        raise ContractError("Phase 41 claim-registry owner is not trusted")
    observed_writers: set[str] = set()
    for ace in aces:
        if ace.inherited:
            raise ContractError("Phase 41 claim-registry DACL contains inherited rules")
        writes = bool(ace.mask & write_control_mask)
        if not writes:
            continue
        if ace.allowed and ace.sid not in allowed_writers:
            raise ContractError("Phase 41 claim-registry grants write control to another SID")
        if ace.allowed:
            observed_writers.add(ace.sid)
        elif ace.sid in allowed_writers:
            raise ContractError("Phase 41 claim-registry denies required writer control")
    if observed_writers != allowed_writers:
        raise ContractError("Phase 41 claim-registry required writer grants are incomplete")


def _registry_acl_snapshot(root: Path) -> tuple[str, bool, tuple[_RegistryAce, ...]]:
    if os.name != "nt":
        raise ContractError("Phase 41 production access requires Windows")
    import ctypes
    from ctypes import wintypes

    SE_FILE_OBJECT = 1
    OWNER_SECURITY_INFORMATION = 0x00000001
    DACL_SECURITY_INFORMATION = 0x00000004
    SE_DACL_PROTECTED = 0x1000
    INHERITED_ACE = 0x10
    ACCESS_ALLOWED_ACE_TYPE = 0
    ACCESS_DENIED_ACE_TYPE = 1

    class ACL(ctypes.Structure):
        _fields_ = [
            ("AclRevision", ctypes.c_ubyte),
            ("Sbz1", ctypes.c_ubyte),
            ("AclSize", wintypes.WORD),
            ("AceCount", wintypes.WORD),
            ("Sbz2", wintypes.WORD),
        ]

    class ACE_HEADER(ctypes.Structure):
        _fields_ = [
            ("AceType", ctypes.c_ubyte),
            ("AceFlags", ctypes.c_ubyte),
            ("AceSize", wintypes.WORD),
        ]

    advapi32 = ctypes.WinDLL("advapi32", use_last_error=True)
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    owner = ctypes.c_void_p()
    dacl = ctypes.c_void_p()
    descriptor = ctypes.c_void_p()
    advapi32.GetNamedSecurityInfoW.argtypes = [
        wintypes.LPWSTR,
        ctypes.c_int,
        wintypes.DWORD,
        ctypes.POINTER(ctypes.c_void_p),
        ctypes.POINTER(ctypes.c_void_p),
        ctypes.POINTER(ctypes.c_void_p),
        ctypes.POINTER(ctypes.c_void_p),
        ctypes.POINTER(ctypes.c_void_p),
    ]
    advapi32.GetNamedSecurityInfoW.restype = wintypes.DWORD
    advapi32.GetSecurityDescriptorControl.argtypes = [
        ctypes.c_void_p,
        ctypes.POINTER(wintypes.WORD),
        ctypes.POINTER(wintypes.DWORD),
    ]
    advapi32.GetSecurityDescriptorControl.restype = wintypes.BOOL
    advapi32.GetAce.argtypes = [
        ctypes.c_void_p,
        wintypes.DWORD,
        ctypes.POINTER(ctypes.c_void_p),
    ]
    advapi32.GetAce.restype = wintypes.BOOL
    advapi32.ConvertSidToStringSidW.argtypes = [
        ctypes.c_void_p,
        ctypes.POINTER(wintypes.LPWSTR),
    ]
    advapi32.ConvertSidToStringSidW.restype = wintypes.BOOL
    kernel32.LocalFree.argtypes = [ctypes.c_void_p]
    kernel32.LocalFree.restype = ctypes.c_void_p
    status = int(
        advapi32.GetNamedSecurityInfoW(
            os.fspath(root),
            SE_FILE_OBJECT,
            OWNER_SECURITY_INFORMATION | DACL_SECURITY_INFORMATION,
            ctypes.byref(owner),
            None,
            ctypes.byref(dacl),
            None,
            ctypes.byref(descriptor),
        )
    )
    if status != 0 or not descriptor.value or not owner.value or not dacl.value:
        raise ContractError("Phase 41 claim-registry security descriptor is unavailable")

    def sid_text(pointer: ctypes.c_void_p) -> str:
        text = wintypes.LPWSTR()
        if not advapi32.ConvertSidToStringSidW(pointer, ctypes.byref(text)):
            raise ContractError("Phase 41 claim-registry SID conversion failed")
        try:
            return str(text.value)
        finally:
            kernel32.LocalFree(ctypes.cast(text, ctypes.c_void_p))

    try:
        control = wintypes.WORD()
        revision = wintypes.DWORD()
        if not advapi32.GetSecurityDescriptorControl(
            descriptor, ctypes.byref(control), ctypes.byref(revision)
        ):
            raise ContractError("Phase 41 claim-registry DACL control is unavailable")
        acl = ctypes.cast(dacl, ctypes.POINTER(ACL)).contents
        rows: list[_RegistryAce] = []
        for index in range(int(acl.AceCount)):
            ace_pointer = ctypes.c_void_p()
            if not advapi32.GetAce(dacl, index, ctypes.byref(ace_pointer)):
                raise ContractError("Phase 41 claim-registry ACE is unavailable")
            header = ctypes.cast(ace_pointer, ctypes.POINTER(ACE_HEADER)).contents
            if header.AceType not in {ACCESS_ALLOWED_ACE_TYPE, ACCESS_DENIED_ACE_TYPE}:
                raise ContractError("Phase 41 claim-registry has an unsupported ACE type")
            mask = ctypes.c_uint32.from_address(ace_pointer.value + 4).value
            sid_pointer = ctypes.c_void_p(ace_pointer.value + 8)
            rows.append(
                _RegistryAce(
                    sid=sid_text(sid_pointer),
                    mask=int(mask),
                    allowed=header.AceType == ACCESS_ALLOWED_ACE_TYPE,
                    inherited=bool(header.AceFlags & INHERITED_ACE),
                )
            )
        return sid_text(owner), bool(control.value & SE_DACL_PROTECTED), tuple(rows)
    finally:
        kernel32.LocalFree(descriptor)


def _validate_claim_registry_root(root: Path) -> None:
    if _TEST_RUNTIME.get() is not None:
        if not root.is_dir() or root.is_symlink():
            raise ContractError("synthetic claim registry is missing or unsafe")
        return
    program_data = _known_program_data_root()
    expected = program_data / "VNPhish" / "phase41-one-shot-claims"
    if ntpath.normcase(ntpath.normpath(os.fspath(root))) != ntpath.normcase(
        ntpath.normpath(os.fspath(expected))
    ):
        raise ContractError("Phase 41 claim registry differs from the Known Folder path")
    for component in (program_data, program_data / "VNPhish", expected):
        attributes = _windows_file_attributes(component)
        if not attributes & 0x10 or attributes & 0x400:
            raise ContractError(
                "ProgramData claim-registry ancestry must be provisioned and non-reparse"
            )
    operator_sid = _current_operator_sid()
    owner_sid, protected, aces = _registry_acl_snapshot(expected)
    _validate_registry_acl_snapshot(
        owner_sid=owner_sid,
        dacl_protected=protected,
        aces=aces,
        operator_sid=operator_sid,
    )


def _current_operator_sid() -> str:
    if _TEST_RUNTIME.get() is not None:
        return "synthetic-operator-sid"
    if os.name != "nt":
        return "synthetic-nonwindows"
    import ctypes
    from ctypes import wintypes

    TOKEN_QUERY = 0x0008
    TOKEN_USER_CLASS = 1
    advapi32 = ctypes.WinDLL("advapi32", use_last_error=True)
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.GetCurrentProcess.restype = wintypes.HANDLE
    advapi32.OpenProcessToken.argtypes = [
        wintypes.HANDLE,
        wintypes.DWORD,
        ctypes.POINTER(wintypes.HANDLE),
    ]
    advapi32.OpenProcessToken.restype = wintypes.BOOL
    advapi32.GetTokenInformation.argtypes = [
        wintypes.HANDLE,
        ctypes.c_uint,
        ctypes.c_void_p,
        wintypes.DWORD,
        ctypes.POINTER(wintypes.DWORD),
    ]
    advapi32.GetTokenInformation.restype = wintypes.BOOL
    advapi32.ConvertSidToStringSidW.argtypes = [
        ctypes.c_void_p,
        ctypes.POINTER(wintypes.LPWSTR),
    ]
    advapi32.ConvertSidToStringSidW.restype = wintypes.BOOL
    token = wintypes.HANDLE()
    if not advapi32.OpenProcessToken(
        kernel32.GetCurrentProcess(), TOKEN_QUERY, ctypes.byref(token)
    ):
        raise ContractError("cannot read the Phase 41 operator SID")
    try:
        needed = wintypes.DWORD()
        advapi32.GetTokenInformation(
            token, TOKEN_USER_CLASS, None, 0, ctypes.byref(needed)
        )
        if not needed.value:
            raise ContractError("operator SID size query failed")
        buffer = ctypes.create_string_buffer(needed.value)
        if not advapi32.GetTokenInformation(
            token,
            TOKEN_USER_CLASS,
            buffer,
            needed,
            ctypes.byref(needed),
        ):
            raise ContractError("operator SID query failed")
        sid_pointer = ctypes.cast(buffer, ctypes.POINTER(ctypes.c_void_p))[0]
        string_sid = wintypes.LPWSTR()
        if not advapi32.ConvertSidToStringSidW(sid_pointer, ctypes.byref(string_sid)):
            raise ContractError("operator SID conversion failed")
        try:
            return string_sid.value
        finally:
            kernel32.LocalFree(ctypes.cast(string_sid, ctypes.c_void_p))
    finally:
        kernel32.CloseHandle(token)


def _exclusive_global_claim_write(path: Path, payload: bytes) -> Path:
    """Create the machine claim with no sharing, write-through, and durable flush."""

    root = _claim_registry_root()
    if path.parent != root:
        raise ContractError("global claim path escaped the fixed registry")
    _validate_claim_registry_root(root)
    if os.name != "nt":
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        try:
            os.write(descriptor, payload)
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
        return path

    import ctypes
    from ctypes import wintypes

    GENERIC_WRITE = 0x40000000
    CREATE_NEW = 1
    FILE_ATTRIBUTE_NORMAL = 0x80
    FILE_FLAG_WRITE_THROUGH = 0x80000000
    invalid_handle = ctypes.c_void_p(-1).value
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    create_file = kernel32.CreateFileW
    create_file.argtypes = [
        wintypes.LPCWSTR,
        wintypes.DWORD,
        wintypes.DWORD,
        ctypes.c_void_p,
        wintypes.DWORD,
        wintypes.DWORD,
        wintypes.HANDLE,
    ]
    create_file.restype = wintypes.HANDLE
    handle = create_file(
        os.fspath(path),
        GENERIC_WRITE,
        0,
        None,
        CREATE_NEW,
        FILE_ATTRIBUTE_NORMAL | FILE_FLAG_WRITE_THROUGH,
        None,
    )
    if handle == invalid_handle:
        code = ctypes.get_last_error()
        if code in {80, 183}:
            raise FileExistsError(os.fspath(path))
        raise OSError(code, "CreateFileW failed for protected Phase 41 claim")
    try:
        written = wintypes.DWORD()
        buffer = ctypes.create_string_buffer(payload)
        if not kernel32.WriteFile(
            handle, buffer, len(payload), ctypes.byref(written), None
        ) or written.value != len(payload):
            raise OSError(ctypes.get_last_error(), "WriteFile failed for Phase 41 claim")
        if not kernel32.FlushFileBuffers(handle):
            raise OSError(
                ctypes.get_last_error(), "FlushFileBuffers failed for Phase 41 claim"
            )
    finally:
        kernel32.CloseHandle(handle)
    return path


class Phase41PrototypeError(RuntimeError):
    """Base error for the one-shot prototype."""


class ContractError(Phase41PrototypeError):
    """An immutable input or artifact violates the prototype contract."""


class AlreadySpentError(Phase41PrototypeError):
    """The durable one-shot claim already exists."""


class AuthorizationError(Phase41PrototypeError):
    """The explicit local authorization is absent or invalid."""


@dataclass(frozen=True, slots=True)
class ModelIdentity:
    role: str
    run_id: str
    model_family: str
    adaptation_mode: str
    artifact_sha256: str
    selected_checkpoint_identity: str

    def __post_init__(self) -> None:
        if self.role not in ("qwen", "phobert"):
            raise ContractError("model role must be qwen or phobert")
        if not SAFE_ID_RE.fullmatch(self.run_id):
            raise ContractError("model run_id is not a safe identifier")
        expected = {
            "qwen": ("qwen", "qlora"),
            "phobert": ("phobert", "classification_head"),
        }[self.role]
        if (self.model_family, self.adaptation_mode) != expected:
            raise ContractError("model family/adaptation mode differs from its fixed role")
        _require_sha256(self.artifact_sha256, "model artifact")
        checkpoint_prefix = (
            "adapter-state-sha256:"
            if self.role == "qwen"
            else "model-state-sha256:"
        )
        if not self.selected_checkpoint_identity.startswith(checkpoint_prefix):
            raise ContractError("selected checkpoint identity has the wrong model-family prefix")
        _require_sha256(
            self.selected_checkpoint_identity.removeprefix(checkpoint_prefix),
            "selected checkpoint",
        )

    def as_dict(self) -> dict[str, str]:
        return {
            "role": self.role,
            "run_id": self.run_id,
            "model_family": self.model_family,
            "adaptation_mode": self.adaptation_mode,
            "artifact_sha256": self.artifact_sha256,
            "selected_checkpoint_identity": self.selected_checkpoint_identity,
        }


@dataclass(frozen=True, slots=True)
class SplitIdentity:
    path: str
    records: int
    bytes: int
    sha256: str
    label_counts: tuple[tuple[str, int], ...]

    def __post_init__(self) -> None:
        if not isinstance(self.path, str) or not self.path.strip():
            raise ContractError("reserved split path must be non-empty")
        if not isinstance(self.records, int) or isinstance(self.records, bool) or self.records <= 0:
            raise ContractError("reserved split record count must be positive")
        if not isinstance(self.bytes, int) or isinstance(self.bytes, bool) or self.bytes <= 0:
            raise ContractError("reserved split byte count must be positive")
        _require_sha256(self.sha256, "reserved split")
        if tuple(label for label, _ in self.label_counts) != LABEL_ORDER:
            raise ContractError("reserved split label counts must follow the fixed label order")
        if any(
            not isinstance(count, int) or isinstance(count, bool) or count <= 0
            for _, count in self.label_counts
        ):
            raise ContractError("reserved split must have positive support for every label")
        if sum(count for _, count in self.label_counts) != self.records:
            raise ContractError("reserved split label counts do not sum to its record count")

    def as_dict(self) -> dict[str, object]:
        return {
            "path": self.path,
            "records": self.records,
            "bytes": self.bytes,
            "sha256": self.sha256,
            "label_counts": {label: count for label, count in self.label_counts},
        }


@dataclass(frozen=True, slots=True)
class InferenceRow:
    row_id: str
    sequence_index: int
    text: str


@dataclass(frozen=True, slots=True)
class InMemorySnapshot:
    """Immutable predictor view; gold labels are intentionally not exposed."""

    rows: tuple[InferenceRow, ...]


@dataclass(frozen=True, slots=True)
class Prediction:
    row_id: str
    predicted_state: str
    raw_output: str
    parser_error: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.row_id, str) or not self.row_id:
            raise ContractError("prediction row_id must be non-empty")
        if self.predicted_state not in PREDICTION_COLUMNS:
            raise ContractError("prediction state is outside the fixed output columns")
        if not isinstance(self.raw_output, str):
            raise ContractError("prediction raw_output must be a string")
        if self.parser_error is not None and not isinstance(self.parser_error, str):
            raise ContractError("prediction parser_error must be a string or null")
        if self.predicted_state == "invalid_output" and (
            not self.parser_error or not SAFE_PARSER_ERROR_RE.fullmatch(self.parser_error)
        ):
            raise ContractError("invalid_output predictions require a fixed safe parser-error code")
        if self.predicted_state != "invalid_output" and self.parser_error is not None:
            raise ContractError("valid predictions cannot carry a parser_error")


@dataclass(frozen=True, slots=True)
class _EvaluationRow:
    inference: InferenceRow
    source_row_sha256: str
    gold_label: str


@dataclass(frozen=True, slots=True)
class _LoadedSnapshot:
    predictor_view: InMemorySnapshot
    rows: tuple[_EvaluationRow, ...]
    payload_bytes: int


@dataclass(frozen=True, slots=True)
class _CompletionProducts:
    result: Mapping[str, object]
    identity: SplitIdentity
    prepared: Mapping[str, object]
    models: tuple[ModelIdentity, ModelIdentity]
    claim_bytes: bytes
    qwen_predictions_bytes: bytes
    phobert_predictions_bytes: bytes
    results_bytes: bytes
    report_bytes: bytes


# Public names emphasize that these values are frozen metadata.  The aliases
# keep the small, independently reviewed prototype representation intact.
FrozenModelIdentity = ModelIdentity
OpaqueHeldOutAuthority = SplitIdentity


@dataclass(frozen=True, slots=True)
class PreparedPhase41Evaluation:
    path: Path
    prepared_sha256: str


@dataclass(frozen=True, slots=True)
class Phase41EvidenceManifest:
    path: Path
    status: str
    evidence_manifest_sha256: str
    artifacts: tuple[tuple[str, str], ...]


@dataclass(frozen=True, slots=True)
class DeploymentFitDisposition:
    choice: str
    selected_checkpoint_identities: tuple[str, str]

    def __post_init__(self) -> None:
        if self.choice not in {"deferred", "authorized_post_evaluation_fit"}:
            raise ContractError("deployment-fit choice is outside the fixed enum")
        if len(self.selected_checkpoint_identities) != 2:
            raise ContractError("deployment-fit disposition requires two checkpoints")
        prefixes = ("adapter-state-sha256:", "model-state-sha256:")
        for identity, prefix in zip(self.selected_checkpoint_identities, prefixes, strict=True):
            if not identity.startswith(prefix):
                raise ContractError("deployment-fit checkpoint identity/order drifted")
            _require_sha256(identity.removeprefix(prefix), "deployment-fit checkpoint")


SplitOpener = Callable[[Path], BinaryIO]
Predictor = Callable[[InMemorySnapshot], Sequence[Prediction]]
Clock = Callable[[], str]
CompletionWriter = Callable[[_CompletionProducts], None]
PreclaimGuard = Callable[[], None]


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _require_sha256(value: object, description: str) -> str:
    if not isinstance(value, str) or not SHA256_RE.fullmatch(value):
        raise ContractError(f"{description} SHA-256 must be 64 lowercase hexadecimal characters")
    return value


def _canonical_json_bytes(value: object) -> bytes:
    return (
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _exclusive_write(path: Path, payload: bytes) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    flags |= getattr(os, "O_BINARY", 0)
    descriptor = os.open(path, flags, 0o600)
    try:
        with os.fdopen(descriptor, "wb", closefd=False) as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
    finally:
        os.close(descriptor)
    return path


def _durable_replace(path: Path, payload: bytes) -> Path:
    """Atomically replace one already-owned journal file with flushed bytes."""

    path = Path(path)
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.replace")
    _exclusive_write(temporary, payload)
    try:
        os.replace(temporary, path)
    except BaseException:
        try:
            temporary.unlink()
        except OSError:
            pass
        raise
    return path


def _replace_global_completion(
    path: Path, *, pending_payload: bytes, completed_payload: bytes
) -> Path:
    """Transition the protected completion journal from pending to completed."""

    root = _claim_registry_root()
    if path.parent != root:
        raise ContractError("global completion path escaped the fixed registry")
    _validate_claim_registry_root(root)
    if path.read_bytes() != pending_payload:
        raise ContractError("protected completion journal changed before finalization")
    return _durable_replace(path, completed_payload)


def _reject_duplicate_keys(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ContractError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _reject_nonfinite_json(value: str) -> object:
    raise ContractError(f"non-finite JSON constant is forbidden: {value}")


def _parse_json_bytes(payload: bytes, description: str) -> dict[str, object]:
    try:
        text = payload.decode("utf-8", errors="strict")
        value = json.loads(
            text,
            object_pairs_hook=_reject_duplicate_keys,
            parse_constant=_reject_nonfinite_json,
        )
    except UnicodeDecodeError as exc:
        raise ContractError(f"{description} is not strict UTF-8") from exc
    except json.JSONDecodeError as exc:
        raise ContractError(f"{description} is not strict JSON") from exc
    if not isinstance(value, dict):
        raise ContractError(f"{description} must be one JSON object")
    return value


def _load_canonical_json(path: Path, description: str) -> tuple[dict[str, object], bytes]:
    candidate = Path(path)
    if not candidate.is_file() or candidate.is_symlink():
        raise ContractError(f"{description} is missing or unsafe")
    payload = candidate.read_bytes()
    value = _parse_json_bytes(payload, description)
    if payload != _canonical_json_bytes(value):
        raise ContractError(f"{description} is not canonical JSON")
    return value, payload


def _parse_models(raw: object) -> tuple[ModelIdentity, ModelIdentity]:
    if not isinstance(raw, list) or len(raw) != 2:
        raise ContractError("evaluation request must contain exactly two model identities")
    models: list[ModelIdentity] = []
    for item in raw:
        if not isinstance(item, dict):
            raise ContractError("model identity must be one object")
        expected_keys = {
            "role",
            "run_id",
            "model_family",
            "adaptation_mode",
            "artifact_sha256",
            "selected_checkpoint_identity",
        }
        if set(item) != expected_keys:
            raise ContractError("model identity fields differ from the fixed contract")
        models.append(ModelIdentity(**item))  # type: ignore[arg-type]
    if tuple(model.role for model in models) != ("qwen", "phobert"):
        raise ContractError("model identities must be ordered Qwen then PhoBERT")
    if len({model.run_id for model in models}) != 2:
        raise ContractError("model run IDs must be unique")
    return models[0], models[1]


def _parse_split_identity(raw: object) -> SplitIdentity:
    if not isinstance(raw, dict):
        raise ContractError("held-out identity must be one object")
    if set(raw) != {"path", "records", "bytes", "sha256", "label_counts"}:
        raise ContractError("held-out identity fields differ from the fixed contract")
    raw_counts = raw["label_counts"]
    if not isinstance(raw_counts, dict) or set(raw_counts) != set(LABEL_ORDER):
        raise ContractError("held-out label counts differ from the fixed label order")
    return SplitIdentity(
        path=raw["path"],  # type: ignore[arg-type]
        records=raw["records"],  # type: ignore[arg-type]
        bytes=raw["bytes"],  # type: ignore[arg-type]
        sha256=raw["sha256"],  # type: ignore[arg-type]
        label_counts=tuple((label, raw_counts[label]) for label in LABEL_ORDER),  # type: ignore[misc]
    )


def _normalize_reserved_path_without_io(path: Path | str) -> str:
    """Validate and normalize the reserved locator without touching its target."""

    raw = os.fspath(path)
    normalized_slashes = raw.replace("/", "\\")
    lowered = normalized_slashes.casefold()
    if lowered.startswith(("\\\\?\\", "\\\\.\\", "\\??\\")):
        raise ContractError("unsafe reserved path namespace")
    drive, tail = ntpath.splitdrive(normalized_slashes)
    if not drive or not ntpath.isabs(normalized_slashes):
        raise ContractError("unsafe reserved path: absolute drive path required")
    if ":" in tail:
        raise ContractError("alternate data stream is forbidden for the reserved path")
    canonical = ntpath.normpath(normalized_slashes)
    if ntpath.normcase(canonical) != ntpath.normcase(normalized_slashes):
        raise ContractError("unsafe reserved path normalization or escape")
    return canonical


def _deployment_fit_precommit(
    choice: str,
    models: Sequence[ModelIdentity],
    *,
    allow_pending: bool = False,
) -> dict[str, object]:
    allowed = {"deferred", "authorized_post_evaluation_fit"}
    if allow_pending:
        allowed.add(PENDING_DEPLOYMENT_FIT_CHOICE)
    if choice not in allowed:
        raise ContractError("deployment-fit precommitment is outside the fixed enum")
    return {
        "choice": choice,
        "selected_checkpoint_identities": [
            model.selected_checkpoint_identity for model in models
        ],
    }


def _freeze_evaluation_request(
    output_root: Path,
    *,
    reserved_split_path: Path | str,
    expected_records: int,
    expected_bytes: int,
    expected_sha256: str,
    expected_label_counts: Mapping[str, int],
    models: Sequence[ModelIdentity],
    deployment_fit_choice: str,
    preparation_scope: str,
    authorities: Mapping[str, object],
    prepared_at_utc: str | None = None,
) -> Path:
    """Internal byte freezer shared by the synthetic and canonical producers."""

    ordered_models = tuple(models)
    if len(ordered_models) != 2 or tuple(model.role for model in ordered_models) != (
        "qwen",
        "phobert",
    ):
        raise ContractError("PREPARED state requires exactly Qwen then PhoBERT")
    if len({model.run_id for model in ordered_models}) != 2:
        raise ContractError("PREPARED model run IDs must be unique")
    if set(expected_label_counts) != set(LABEL_ORDER):
        raise ContractError("expected label counts must contain exactly four labels")
    split = SplitIdentity(
        path=_normalize_reserved_path_without_io(reserved_split_path),
        records=expected_records,
        bytes=expected_bytes,
        sha256=expected_sha256,
        label_counts=tuple((label, expected_label_counts[label]) for label in LABEL_ORDER),
    )
    payload = {
        "schema_version": "phase41-one-shot-request-v1",
        "state": "prepared",
        "preparation_scope": preparation_scope,
        "prepared_at_utc": prepared_at_utc or _utc_now(),
        "held_out": split.as_dict(),
        "models": [model.as_dict() for model in ordered_models],
        "deployment_fit_precommit": _deployment_fit_precommit(
            deployment_fit_choice,
            ordered_models,
            allow_pending=preparation_scope == PRODUCTION_PREPARATION_SCOPE,
        ),
        "authorities": dict(authorities),
        "prediction_policy": {
            "qwen_retries": 0,
            "qwen_repairs": False,
            "phobert_decision": "fixed-four-logit-argmax",
        },
        "report_policy": {
            "terminal_evidence_only": True,
            "model_selection_after_test": False,
            "training_action_after_test": False,
        },
    }
    root = Path(output_root)
    root.mkdir(parents=True, exist_ok=True)
    return _exclusive_write(root / PREPARED_NAME, _canonical_json_bytes(payload))


def prepare_evaluation(
    output_root: Path,
    *,
    reserved_split_path: Path,
    expected_records: int,
    expected_bytes: int,
    expected_sha256: str,
    expected_label_counts: Mapping[str, int],
    models: Sequence[ModelIdentity],
    deployment_fit_choice: str,
    preparation_scope: str,
    authorities: Mapping[str, object] | None = None,
    prepared_at_utc: str | None = None,
) -> Path:
    """Freeze PREPARED state without opening or inspecting the reserved split."""

    if preparation_scope == SYNTHETIC_PREPARATION_SCOPE:
        if _TEST_RUNTIME.get() is None:
            raise ContractError("synthetic preparation is unavailable in production")
    elif preparation_scope == PRODUCTION_PREPARATION_SCOPE:
        raise ContractError(
            f"{PHASE41_PRODUCTION_BOOTSTRAP_REQUIRED}: only the fixed canonical "
            "producer may create production preparation after its live runtime, "
            "source, and protocol bootstrap is explicitly authorized"
        )
    else:
        raise ContractError("evaluation preparation scope is invalid")
    # Opaque by design: do not resolve, normalize, stat, hash, enumerate, or
    # open this declared path during preparation.
    return _freeze_evaluation_request(
        output_root,
        reserved_split_path=reserved_split_path,
        expected_records=expected_records,
        expected_bytes=expected_bytes,
        expected_sha256=expected_sha256,
        expected_label_counts=expected_label_counts,
        models=models,
        deployment_fit_choice=deployment_fit_choice,
        preparation_scope=preparation_scope,
        authorities=dict(authorities or {}),
        prepared_at_utc=prepared_at_utc,
    )


def authorize_evaluation(
    output_root: Path,
    *,
    operator_id: str,
    statement: str,
    deployment_fit_choice: str | None = None,
    authorized_at_utc: str | None = None,
) -> Path:
    """Freeze an explicit, hash-bound local authorization; this is not a signature."""

    signal_choice = _AUTHORIZATION_SIGNAL_CHOICES.get(statement)
    if signal_choice is None:
        raise AuthorizationError(
            "authorization statement does not match an exact Phase 41 signal"
        )
    if (
        deployment_fit_choice is not None
        and deployment_fit_choice != signal_choice
    ):
        raise AuthorizationError(
            "authorization signal and deployment-fit choice differ"
        )
    if not SAFE_ID_RE.fullmatch(operator_id):
        raise AuthorizationError("operator_id is not a safe identifier")
    root = Path(output_root)
    prepared, prepared_bytes = _load_canonical_json(
        root / PREPARED_NAME, "Phase 41 evaluation request"
    )
    _, models = _validate_prepared(prepared)
    _require_canonical_production_authorities(prepared)
    prepared_precommit = prepared["deployment_fit_precommit"]
    assert isinstance(prepared_precommit, dict)
    pending = prepared_precommit.get("choice") == PENDING_DEPLOYMENT_FIT_CHOICE
    if pending:
        effective_precommit = _deployment_fit_precommit(signal_choice, models)
    else:
        if prepared_precommit.get("choice") != signal_choice:
            raise AuthorizationError(
                "authorization signal differs from the prepared deployment-fit choice"
            )
        effective_precommit = dict(prepared_precommit)
    payload: dict[str, object] = {
        "schema_version": "phase41-explicit-authorization-v1",
        "state": "explicitly_authorized",
        "authorization_method": "explicit_local_attestation",
        "operator_id": operator_id,
        "authorized_at_utc": authorized_at_utc or _utc_now(),
        "statement": statement,
        "prepared_sha256": _sha256(prepared_bytes),
        "phase40_authorities_sha256": _phase40_authorities_sha256(prepared),
    }
    if pending:
        payload["schema_version"] = "phase41-explicit-authorization-v2"
        payload["deployment_fit_precommit"] = effective_precommit
        payload["deployment_fit_precommit_sha256"] = _sha256(
            _canonical_json_bytes(effective_precommit)
        )
    try:
        return _exclusive_write(root / AUTHORIZATION_NAME, _canonical_json_bytes(payload))
    except FileExistsError as exc:
        raise AuthorizationError("explicit authorization already exists") from exc


def _validate_prepared(prepared: Mapping[str, object]) -> tuple[
    SplitIdentity, tuple[ModelIdentity, ModelIdentity]
]:
    if set(prepared) != {
        "schema_version",
        "state",
        "preparation_scope",
        "prepared_at_utc",
        "held_out",
        "models",
        "deployment_fit_precommit",
        "authorities",
        "prediction_policy",
        "report_policy",
    }:
        raise ContractError("evaluation request fields differ from the fixed contract")
    if (
        prepared["schema_version"] != "phase41-one-shot-request-v1"
        or prepared["state"] != "prepared"
    ):
        raise ContractError("evaluation request schema/state is invalid")
    preparation_scope = prepared["preparation_scope"]
    if preparation_scope == SYNTHETIC_PREPARATION_SCOPE:
        if _TEST_RUNTIME.get() is None:
            raise ContractError("synthetic evaluation artifacts are rejected in production")
    elif preparation_scope == PRODUCTION_PREPARATION_SCOPE:
        if _TEST_RUNTIME.get() is not None:
            raise ContractError("production evaluation artifacts are rejected in synthetic runtime")
    else:
        raise ContractError("evaluation preparation scope is invalid")
    if prepared["prediction_policy"] != {
        "qwen_retries": 0,
        "qwen_repairs": False,
        "phobert_decision": "fixed-four-logit-argmax",
    }:
        raise ContractError("prediction policy drifted")
    models = _parse_models(prepared["models"])
    precommit = prepared["deployment_fit_precommit"]
    if not isinstance(precommit, dict) or precommit != _deployment_fit_precommit(
        precommit.get("choice") if isinstance(precommit, dict) else "",  # type: ignore[arg-type]
        models,
        allow_pending=preparation_scope == PRODUCTION_PREPARATION_SCOPE,
    ):
        raise ContractError("deployment-fit precommitment drifted")
    authorities = prepared["authorities"]
    if not isinstance(authorities, dict):
        raise ContractError("preauthorization authorities must be an object")
    if authorities:
        expected_authorities = {
            "protocols_sha256",
            "model_bundle_authorities",
            "execution_source_manifest_sha256",
            "comparison_authority_sha256",
            "review_closure_sha256",
            "comparison_launch_receipt_sha256",
            "prior_human_exposure_disclosed",
            *_PHASE40_REQUIRED_AUTHORITY_HASH_FIELDS,
        }
        if preparation_scope == PRODUCTION_PREPARATION_SCOPE:
            expected_authorities.update(_PRODUCTION_EXTRA_AUTHORITY_HASH_FIELDS)
        if set(authorities) != expected_authorities:
            raise ContractError("preauthorization authority fields drifted")
        for name in expected_authorities - {
            "prior_human_exposure_disclosed",
            "model_bundle_authorities",
        }:
            _require_sha256(authorities[name], name)
        bundle_authorities = authorities["model_bundle_authorities"]
        if (
            not isinstance(bundle_authorities, list)
            or len(bundle_authorities) != 2
            or tuple(
                item.get("role") if isinstance(item, dict) else None
                for item in bundle_authorities
            )
            != ("qwen", "phobert")
        ):
            raise ContractError("model bundle authorities are incomplete")
        for item in bundle_authorities:
            if (
                not isinstance(item, dict)
                or set(item) != {"role", "bundle_root", "bundle_root_sha256"}
                or not isinstance(item["bundle_root"], str)
                or not item["bundle_root"]
            ):
                raise ContractError("model bundle authority row drifted")
            _require_sha256(item["bundle_root_sha256"], "model bundle root")
        if authorities["prior_human_exposure_disclosed"] is not True:
            raise ContractError("prior held-out human/content exposure must be disclosed")
    if prepared["report_policy"] != {
        "terminal_evidence_only": True,
        "model_selection_after_test": False,
        "training_action_after_test": False,
    }:
        raise ContractError("terminal report policy drifted")
    identity = _parse_split_identity(prepared["held_out"])
    if identity.path != _normalize_reserved_path_without_io(identity.path):
        raise ContractError("held-out path authority drifted")
    return identity, models


def _require_canonical_production_authorities(
    prepared: Mapping[str, object],
) -> None:
    """Require the complete canonical production closure before authorization."""

    if prepared.get("preparation_scope") != PRODUCTION_PREPARATION_SCOPE:
        return
    precommit = prepared.get("deployment_fit_precommit")
    if not isinstance(precommit, dict) or precommit.get("choice") != (
        PENDING_DEPLOYMENT_FIT_CHOICE
    ):
        raise ContractError("production preparation must await the human fit choice")
    authorities = prepared.get("authorities")
    if not isinstance(authorities, dict):
        raise ContractError("production authorities are missing")
    for name in _PRODUCTION_EXTRA_AUTHORITY_HASH_FIELDS:
        _require_sha256(authorities.get(name), name)
    registry = _claim_registry_authority(_claim_registry_root())
    if authorities["claim_registry_authority_sha256"] != registry[
        "authority_sha256"
    ]:
        raise ContractError("protected claim-registry authority drifted")


def _required_phase40_authority_hashes(
    authorities: Mapping[str, object],
) -> dict[str, str]:
    """Return the future-complete authority hashes bound into every artifact."""

    return {
        name: _require_sha256(authorities.get(name), name)
        for name in _PHASE40_REQUIRED_AUTHORITY_HASH_FIELDS
    }


def _phase40_authorities_sha256(prepared: Mapping[str, object]) -> str:
    authorities = prepared.get("authorities")
    if not isinstance(authorities, dict):
        raise ContractError("preauthorization authorities must be an object")
    bound = {
        "comparison_launch_receipt_sha256": _require_sha256(
            authorities.get("comparison_launch_receipt_sha256"),
            "comparison launch receipt",
        ),
        **_required_phase40_authority_hashes(authorities),
    }
    return _sha256(_canonical_json_bytes(bound))


def _validate_authorization(
    authorization: Mapping[str, object],
    *,
    prepared_sha256: str,
    phase40_authorities_sha256: str,
    prepared_deployment_fit_precommit: Mapping[str, object],
) -> dict[str, object]:
    v1_fields = {
        "schema_version",
        "state",
        "authorization_method",
        "operator_id",
        "authorized_at_utc",
        "statement",
        "prepared_sha256",
        "phase40_authorities_sha256",
    }
    v2_fields = v1_fields | {
        "deployment_fit_precommit",
        "deployment_fit_precommit_sha256",
    }
    schema = authorization.get("schema_version")
    statement = authorization.get("statement")
    signal_choice = (
        _AUTHORIZATION_SIGNAL_CHOICES.get(statement)
        if isinstance(statement, str)
        else None
    )
    if set(authorization) not in (v1_fields, v2_fields):
        raise AuthorizationError("authorization fields differ from the fixed contract")
    if (
        schema not in {
            "phase41-explicit-authorization-v1",
            "phase41-explicit-authorization-v2",
        }
        or authorization["state"] != "explicitly_authorized"
        or authorization["authorization_method"] != "explicit_local_attestation"
        or signal_choice is None
        or authorization["prepared_sha256"] != prepared_sha256
        or authorization["phase40_authorities_sha256"]
        != phase40_authorities_sha256
    ):
        raise AuthorizationError("authorization does not bind the prepared request")
    if not isinstance(authorization["operator_id"], str) or not SAFE_ID_RE.fullmatch(
        authorization["operator_id"]
    ):
        raise AuthorizationError("authorization operator_id is invalid")
    if schema == "phase41-explicit-authorization-v1":
        if set(authorization) != v1_fields:
            raise AuthorizationError("legacy authorization fields drifted")
        if (
            prepared_deployment_fit_precommit.get("choice")
            == PENDING_DEPLOYMENT_FIT_CHOICE
        ):
            raise AuthorizationError(
                "production authorization must record the human deployment-fit choice"
            )
        if prepared_deployment_fit_precommit.get("choice") != signal_choice:
            raise AuthorizationError(
                "authorization signal differs from the prepared deployment-fit choice"
            )
        return dict(prepared_deployment_fit_precommit)
    if set(authorization) != v2_fields:
        raise AuthorizationError("authorization deployment-fit fields drifted")
    precommit = authorization["deployment_fit_precommit"]
    if not isinstance(precommit, dict):
        raise AuthorizationError("authorization deployment-fit precommitment is invalid")
    try:
        parsed = DeploymentFitDisposition(
            choice=str(precommit.get("choice")),
            selected_checkpoint_identities=tuple(
                precommit.get("selected_checkpoint_identities", ())  # type: ignore[arg-type]
            ),
        )
    except (ContractError, TypeError) as exc:
        raise AuthorizationError(
            "authorization deployment-fit precommitment is invalid"
        ) from exc
    expected_identities = prepared_deployment_fit_precommit.get(
        "selected_checkpoint_identities"
    )
    if (
        not isinstance(expected_identities, list)
        or not all(isinstance(value, str) for value in expected_identities)
        or tuple(expected_identities) != parsed.selected_checkpoint_identities
        or parsed.choice != signal_choice
    ):
        raise AuthorizationError(
            "authorization signal and deployment-fit precommitment differ"
        )
    expected_precommit = {
        "choice": signal_choice,
        "selected_checkpoint_identities": list(expected_identities),
    }
    if (
        precommit != expected_precommit
        or authorization["deployment_fit_precommit_sha256"]
        != _sha256(_canonical_json_bytes(expected_precommit))
    ):
        raise AuthorizationError(
            "authorization deployment-fit precommitment is not canonical"
        )
    return expected_precommit


def _provision_claim_registry_root() -> Path:
    """Create the code-fixed protected registry without creating any claim."""

    root = _claim_registry_root()
    if _TEST_RUNTIME.get() is not None:
        root.mkdir(parents=True, exist_ok=True)
        _validate_claim_registry_root(root)
        return root
    try:
        _validate_claim_registry_root(root)
        return root
    except ContractError:
        pass
    root.mkdir(parents=True, exist_ok=True)
    for component in (_known_program_data_root() / "VNPhish", root):
        attributes = _windows_file_attributes(component)
        if not attributes & 0x10 or attributes & 0x400:
            raise ContractError("claim-registry provisioning encountered a reparse path")
    operator_sid = _current_operator_sid()
    creation_flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    commands = (
        ("icacls", os.fspath(root), "/setowner", f"*{operator_sid}"),
        (
            "icacls",
            os.fspath(root),
            "/inheritance:r",
            "/grant:r",
            f"*{operator_sid}:(OI)(CI)F",
            "*S-1-5-18:(OI)(CI)F",
            "*S-1-5-32-544:(OI)(CI)F",
        ),
    )
    for command in commands:
        completed = subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
            creationflags=creation_flags,
        )
        if completed.returncode != 0:
            raise ContractError("failed to provision the protected claim-registry ACL")
    _validate_claim_registry_root(root)
    return root


def _claim_registry_authority(root: Path) -> dict[str, object]:
    """Freeze the fixed path and exact protected ACL without listing claims."""

    _validate_claim_registry_root(root)
    owner_sid, protected, aces = _registry_acl_snapshot(root)
    rows = sorted(
        (
            {
                "sid": ace.sid,
                "mask": ace.mask,
                "allowed": ace.allowed,
                "inherited": ace.inherited,
            }
            for ace in aces
        ),
        key=lambda item: (
            str(item["sid"]),
            int(item["mask"]),
            bool(item["allowed"]),
            bool(item["inherited"]),
        ),
    )
    rendered = ntpath.normpath(os.fspath(root))
    core: dict[str, object] = {
        "path": rendered,
        "path_sha256": _sha256(ntpath.normcase(rendered).encode("utf-8")),
        "owner_sid": owner_sid,
        "dacl_protected": protected,
        "aces": rows,
    }
    core["authority_sha256"] = _sha256(_canonical_json_bytes(core))
    return core
    if (
        list(parsed.selected_checkpoint_identities) != expected_identities
        or authorization["deployment_fit_precommit_sha256"]
        != _sha256(_canonical_json_bytes(precommit))
    ):
        raise AuthorizationError("authorization deployment-fit precommitment drifted")
    return dict(precommit)


def _global_claim_path(identity: SplitIdentity) -> Path:
    """Return the one repository-local claim shared by every path/output root.

    The registry location is fixed by this module and the filename is derived
    only from the frozen split SHA-256. Computing it does not stat or open the
    split.
    """

    return _claim_registry_root() / f"{identity.sha256}.claim.json"


def _global_completion_path(identity: SplitIdentity) -> Path:
    return _claim_registry_root() / f"{identity.sha256}.completion.json"


def _assert_unspent_and_clean(root: Path, global_claim: Path) -> None:
    global_completion = global_claim.with_name(
        global_claim.name.removesuffix(".claim.json") + ".completion.json"
    )
    local_claim = root / CLAIM_NAME
    if (
        local_claim.exists()
        or local_claim.is_symlink()
        or global_claim.exists()
        or global_claim.is_symlink()
        or global_completion.exists()
        or global_completion.is_symlink()
    ):
        raise AlreadySpentError("the Phase 41 holdout already has a durable claim")
    for name in _PRECLAIM_OUTPUT_NAMES:
        candidate = root / name
        if candidate.exists() or candidate.is_symlink():
            raise ContractError(f"pre-claim output already exists: {name}")


def _claim_once(
    root: Path,
    *,
    identity: SplitIdentity,
    prepared_sha256: str,
    authorization_sha256: str,
    materialization_receipt_sha256: str,
    deployment_fit_precommit_sha256: str,
    claimed_at_utc: str,
    clock: Clock,
) -> tuple[Path, bytes]:
    payload = _canonical_json_bytes(
        {
            "schema_version": "phase41-one-shot-claim-v1",
            "state": "spent",
            "claimed_at_utc": claimed_at_utc,
            "prepared_sha256": prepared_sha256,
            "authorization_sha256": authorization_sha256,
            "execution_materialization_receipt_sha256": materialization_receipt_sha256,
            "deployment_fit_precommit_sha256": deployment_fit_precommit_sha256,
            "reserved_split_sha256": identity.sha256,
            "reserved_split_path_sha256": _sha256(identity.path.encode("utf-8")),
            "claim_registry_sha256": _sha256(
                os.fspath(_claim_registry_root()).encode("utf-8")
            ),
            "operator_sid": _current_operator_sid(),
            "meaning": "existence permanently blocks another governed evaluation attempt",
        }
    )
    global_path = _global_claim_path(identity)
    try:
        _exclusive_global_claim_write(global_path, payload)
    except FileExistsError as exc:
        raise AlreadySpentError("the Phase 41 holdout was claimed concurrently") from exc
    # The machine-global claim is already authoritative at this point. If the
    # local receipt cannot be frozen, preserve a terminal spent-failed record
    # before propagating; a retry remains forbidden by the global claim.
    try:
        _exclusive_write(root / CLAIM_NAME, payload)
    except BaseException as exc:
        _terminal_failure(
            root,
            _sha256(payload),
            "freeze_local_claim",
            exc,
            clock,
        )
        raise
    _emit_test_event("claim_durable")
    return global_path, payload


def _decode_split_rows(payload: bytes, identity: SplitIdentity) -> _LoadedSnapshot:
    if len(payload) != identity.bytes:
        raise ContractError(
            f"held-out byte count mismatch: expected {identity.bytes}, got {len(payload)}"
        )
    digest = _sha256(payload)
    if digest != identity.sha256:
        raise ContractError("held-out SHA-256 mismatch")
    try:
        text = payload.decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise ContractError("held-out payload is not strict UTF-8") from exc
    if "\r" in text:
        raise ContractError("held-out payload contains unsupported CR bytes")
    if not text:
        raise ContractError("held-out payload is empty")
    framed = text[:-1].split("\n") if text.endswith("\n") else text.split("\n")
    if not framed or any(not line for line in framed):
        raise ContractError("held-out payload contains a blank JSONL record")

    evaluation_rows: list[_EvaluationRow] = []
    support = {label: 0 for label in LABEL_ORDER}
    cursor = 0
    for index, line in enumerate(framed):
        line_bytes = line.encode("utf-8")
        raw = _parse_json_bytes(line_bytes, f"held-out record {index}")
        if set(raw) != DATASET_KEYS:
            raise ContractError("held-out record fields differ from the fixed dataset schema")
        text_value = raw["text"]
        label = raw["label"]
        if not isinstance(text_value, str) or not text_value:
            raise ContractError("held-out record text must be non-empty")
        if label not in LABEL_ORDER:
            raise ContractError("held-out record label is outside the fixed order")
        if not isinstance(raw["suspicious_spans"], list) or not all(
            isinstance(item, str) for item in raw["suspicious_spans"]
        ):
            raise ContractError("held-out suspicious_spans must be a string list")
        for field in ("risk_tier", "xai_explanation", "source", "seed_id"):
            if not isinstance(raw[field], str) or not raw[field]:
                raise ContractError(f"held-out {field} must be non-empty text")
        source_sha = _sha256(line_bytes)
        row_digest = hashlib.sha256(
            b"phase41-inference-row-v2\0"
            + str(index).encode("ascii")
            + b"\0"
            + text_value.encode("utf-8")
        ).hexdigest()
        inference = InferenceRow(
            row_id=f"p41-row-v2-{row_digest}",
            sequence_index=index,
            text=text_value,
        )
        evaluation_rows.append(
            _EvaluationRow(
                inference=inference,
                source_row_sha256=source_sha,
                gold_label=label,
            )
        )
        support[label] += 1
        cursor += len(line_bytes)
    if len(evaluation_rows) != identity.records:
        raise ContractError(
            f"held-out record count mismatch: expected {identity.records}, got {len(evaluation_rows)}"
        )
    if support != dict(identity.label_counts):
        raise ContractError("held-out label support differs from the prepared authority")
    public = InMemorySnapshot(rows=tuple(row.inference for row in evaluation_rows))
    return _LoadedSnapshot(public, tuple(evaluation_rows), len(payload))


def _open_snapshot_once(identity: SplitIdentity, opener: SplitOpener) -> _LoadedSnapshot:
    # This is the only reserved-split opener call in the prototype.
    handle = opener(Path(identity.path))
    _emit_test_event("handle_acquired")
    try:
        payload = handle.read()
        _emit_test_event("payload_read")
    finally:
        handle.close()
    if not isinstance(payload, bytes):
        raise ContractError("reserved split opener must return a binary stream")
    return _decode_split_rows(payload, identity)


def _validated_predictions(
    predictions: Sequence[Prediction],
    snapshot: InMemorySnapshot,
    *,
    role: str,
) -> tuple[Prediction, ...]:
    rows = tuple(predictions)
    if len(rows) != len(snapshot.rows):
        raise ContractError(f"{role} prediction count differs from the in-memory snapshot")
    for expected, prediction in zip(snapshot.rows, rows, strict=True):
        if not isinstance(prediction, Prediction):
            raise ContractError(f"{role} predictor returned a non-Prediction value")
        if prediction.row_id != expected.row_id:
            raise ContractError(f"{role} prediction order/identity differs from the snapshot")
    if len({row.row_id for row in rows}) != len(rows):
        raise ContractError(f"{role} predictions contain duplicate row IDs")
    return rows


def _safe_divide(numerator: int, denominator: int) -> float:
    return 0.0 if denominator == 0 else numerator / denominator


def compute_metrics(
    gold_labels: Sequence[str], predictions: Sequence[Prediction]
) -> dict[str, object]:
    gold = tuple(gold_labels)
    predicted = tuple(row.predicted_state for row in predictions)
    if not gold or len(gold) != len(predicted):
        raise ContractError("metrics require equal non-empty gold and prediction sequences")
    if any(label not in LABEL_ORDER for label in gold):
        raise ContractError("metric gold labels differ from the fixed label order")
    if any(label not in PREDICTION_COLUMNS for label in predicted):
        raise ContractError("metric predictions differ from the fixed output columns")

    matrix = [[0 for _ in PREDICTION_COLUMNS] for _ in LABEL_ORDER]
    for gold_label, predicted_label in zip(gold, predicted, strict=True):
        matrix[LABEL_ORDER.index(gold_label)][PREDICTION_COLUMNS.index(predicted_label)] += 1

    per_class: list[dict[str, object]] = []
    for label_index, label in enumerate(LABEL_ORDER):
        true_positive = matrix[label_index][label_index]
        support = sum(matrix[label_index])
        predicted_total = sum(row[label_index] for row in matrix)
        precision = _safe_divide(true_positive, predicted_total)
        recall = _safe_divide(true_positive, support)
        f1 = 0.0 if precision + recall == 0 else 2 * precision * recall / (precision + recall)
        per_class.append(
            {
                "label": label,
                "precision": precision,
                "recall": recall,
                "f1": f1,
                "support": support,
            }
        )

    evaluated_rows = len(gold)
    macro_f1 = sum(float(row["f1"]) for row in per_class) / len(LABEL_ORDER)
    weighted_f1 = sum(
        float(row["f1"]) * int(row["support"]) for row in per_class
    ) / evaluated_rows
    correct = sum(
        gold_label == predicted_label
        for gold_label, predicted_label in zip(gold, predicted, strict=True)
    )
    invalid_count = predicted.count("invalid_output")
    risky_to_benign = sum(
        gold_label in RISKY_LABELS and predicted_label == "benign"
        for gold_label, predicted_label in zip(gold, predicted, strict=True)
    )
    risky_to_invalid = sum(
        gold_label in RISKY_LABELS and predicted_label == "invalid_output"
        for gold_label, predicted_label in zip(gold, predicted, strict=True)
    )
    return {
        "label_order": list(LABEL_ORDER),
        "prediction_columns": list(PREDICTION_COLUMNS),
        "evaluated_rows": evaluated_rows,
        "per_class": per_class,
        "macro_f1": macro_f1,
        "weighted_f1": weighted_f1,
        "accuracy": correct / evaluated_rows,
        "confusion_matrix": matrix,
        "invalid_output_count": invalid_count,
        "invalid_output_rate": invalid_count / evaluated_rows,
        "risky_to_benign_count": risky_to_benign,
        "risky_to_invalid_count": risky_to_invalid,
    }


def _comparison_values(metrics: Mapping[str, object]) -> tuple[tuple[str, float, bool], ...]:
    values: list[tuple[str, float, bool]] = [
        ("macro_f1", float(metrics["macro_f1"]), True),
        ("weighted_f1", float(metrics["weighted_f1"]), True),
        ("accuracy", float(metrics["accuracy"]), True),
    ]
    per_class = metrics["per_class"]
    if not isinstance(per_class, list):
        raise ContractError("per_class metrics are malformed")
    for expected_label, raw in zip(LABEL_ORDER, per_class, strict=True):
        if not isinstance(raw, dict) or raw.get("label") != expected_label:
            raise ContractError("per_class metrics do not follow the fixed label order")
        for metric in ("precision", "recall", "f1"):
            values.append((f"{expected_label}.{metric}", float(raw[metric]), True))
    for metric in (
        "invalid_output_count",
        "risky_to_benign_count",
        "risky_to_invalid_count",
    ):
        values.append((f"{metric}(lower_is_better)", float(metrics[metric]), False))
    return tuple(values)


def comparison_statements(
    qwen_metrics: Mapping[str, object], phobert_metrics: Mapping[str, object]
) -> tuple[str, str, str]:
    qwen_values = _comparison_values(qwen_metrics)
    phobert_values = _comparison_values(phobert_metrics)
    phobert_higher: list[str] = []
    qwen_higher: list[str] = []
    ties: list[str] = []
    for (name, qwen, higher_is_better), (other_name, phobert, other_direction) in zip(
        qwen_values, phobert_values, strict=True
    ):
        if name != other_name or higher_is_better != other_direction:
            raise ContractError("metric comparison orders differ")
        if math.isclose(qwen, phobert, rel_tol=0.0, abs_tol=1e-12):
            ties.append(name)
        elif (phobert > qwen) == higher_is_better:
            phobert_higher.append(name)
        else:
            qwen_higher.append(name)

    def line(prefix: str, values: Sequence[str]) -> str:
        return f"{prefix}: {', '.join(values) if values else 'none'}."

    return (
        line("PhoBERT higher on", phobert_higher),
        line("Qwen higher on", qwen_higher),
        line("Ties", ties),
    )


def _prediction_jsonl(
    role: str,
    run_id: str,
    rows: Sequence[_EvaluationRow],
    predictions: Sequence[Prediction],
) -> bytes:
    chunks: list[bytes] = []
    for evaluation_row, prediction in zip(rows, predictions, strict=True):
        chunks.append(
            _canonical_json_bytes(
                {
                    "schema_version": "phase41-prediction-row-v1",
                    "model_role": role,
                    "model_run_id": run_id,
                    "row_id": prediction.row_id,
                    "sequence_index": evaluation_row.inference.sequence_index,
                    "source_row_sha256": evaluation_row.source_row_sha256,
                    "gold_label": evaluation_row.gold_label,
                    "predicted_state": prediction.predicted_state,
                    # Retain parser evidence without duplicating a model output
                    # that could echo the reserved message text.
                    "raw_output_bytes": len(prediction.raw_output.encode("utf-8")),
                    "raw_output_sha256": _sha256(prediction.raw_output.encode("utf-8")),
                    "parser_error": prediction.parser_error,
                }
            )
        )
    return b"".join(chunks)


def _render_report(result: Mapping[str, object]) -> bytes:
    models = result["models"]
    if not isinstance(models, list) or len(models) != 2:
        raise ContractError("result report requires exactly two models")
    lines = [
        "# Phase 41 One-Shot Two-Model Evaluation",
        "",
        "This artifact contains terminal descriptive measurements only.",
        "The partition had prior human/content exposure during corpus-quality review; this is one post-freeze model-evaluation pass, not a claim of human blindness.",
        "Poor results are terminal evidence and cannot trigger tuning, checkpoint selection, contingency activation, or dataset repair on this partition.",
        "",
    ]
    for model in models:
        if not isinstance(model, dict) or not isinstance(model.get("metrics"), dict):
            raise ContractError("result model entry is malformed")
        metrics = model["metrics"]
        lines.extend(
            [
                f"## {model['role']} ({model['run_id']})",
                "",
                f"- macro_f1: {float(metrics['macro_f1']):.6f}",
                f"- weighted_f1: {float(metrics['weighted_f1']):.6f}",
                f"- accuracy: {float(metrics['accuracy']):.6f}",
                f"- invalid_output_count: {metrics['invalid_output_count']}",
                f"- risky_to_benign_count: {metrics['risky_to_benign_count']}",
                f"- risky_to_invalid_count: {metrics['risky_to_invalid_count']}",
                "",
                "| label | precision | recall | f1 | support |",
                "|---|---:|---:|---:|---:|",
            ]
        )
        for row in metrics["per_class"]:
            lines.append(
                f"| {row['label']} | {float(row['precision']):.6f} | "
                f"{float(row['recall']):.6f} | {float(row['f1']):.6f} | {row['support']} |"
            )
        if metrics.get("label_order") != list(LABEL_ORDER):
            raise ContractError("report confusion matrix label order drifted")
        if metrics.get("prediction_columns") != list(PREDICTION_COLUMNS):
            raise ContractError("report confusion matrix prediction columns drifted")
        matrix = metrics.get("confusion_matrix")
        if not isinstance(matrix, list) or len(matrix) != len(LABEL_ORDER):
            raise ContractError("report confusion matrix row count is malformed")
        validated_matrix: list[list[int]] = []
        for row_index, raw_matrix_row in enumerate(matrix):
            if (
                not isinstance(raw_matrix_row, list)
                or len(raw_matrix_row) != len(PREDICTION_COLUMNS)
                or any(
                    not isinstance(value, int) or isinstance(value, bool) or value < 0
                    for value in raw_matrix_row
                )
            ):
                raise ContractError(
                    f"report confusion matrix row {row_index} is malformed"
                )
            validated_matrix.append(raw_matrix_row)
        lines.extend(
            [
                "",
                "### Confusion matrix",
                "",
                "Rows are gold labels; columns are predicted states.",
                "",
                "| gold label / predicted state | "
                + " | ".join(PREDICTION_COLUMNS)
                + " |",
                "|---|" + "---:|" * len(PREDICTION_COLUMNS),
            ]
        )
        for gold_label, matrix_row in zip(
            LABEL_ORDER, validated_matrix, strict=True
        ):
            lines.append(
                f"| {gold_label} | "
                + " | ".join(str(value) for value in matrix_row)
                + " |"
            )
        lines.append("")
    lines.extend(["## Plain comparison", ""])
    lines.extend(f"- {statement}" for statement in result["comparison_statements"])
    lines.append("")
    return ("\n".join(lines)).encode("utf-8")


def _terminal_failure(root: Path, claim_sha256: str, stage: str, exc: BaseException, clock: Clock) -> None:
    payload = {
        "schema_version": "phase41-terminal-v1",
        "status": "spent_failed",
        "completed_at_utc": clock(),
        "claim_sha256": claim_sha256,
        "failure_stage": stage,
        "error_type": type(exc).__name__,
        "rerun_permitted": False,
    }
    terminal_path = root / TERMINAL_NAME
    terminal_payload = _canonical_json_bytes(payload)
    try:
        _exclusive_write(terminal_path, terminal_payload)
    except FileExistsError:
        # A local completed terminal is only provisional until the protected
        # completion journal reaches completed. Replace it deterministically
        # when that final transition fails; the global claim remains spent.
        _durable_replace(terminal_path, terminal_payload)


def _run_once(
    output_root: Path,
    *,
    opener: SplitOpener,
    qwen_predictor: Predictor,
    phobert_predictor: Predictor,
    completion_writer: CompletionWriter,
    preclaim_guard: PreclaimGuard,
    clock: Clock = _utc_now,
) -> dict[str, object]:
    """Consume authorization and permanently spend the holdout.

    Predictors must already be loaded, identity-checked, and smoke-tested by the
    caller before entry. Model loading inside either callback is a contract
    violation because a load failure would needlessly spend the one-shot run.
    """

    if _TEST_RUNTIME.get() is None:
        raise ContractError("synthetic callback execution is unavailable in production")
    root = Path(output_root)
    prepared, prepared_bytes = _load_canonical_json(
        root / PREPARED_NAME, "Phase 41 evaluation request"
    )
    identity, models = _validate_prepared(prepared)
    _require_canonical_production_authorities(prepared)
    authorization, authorization_bytes = _load_canonical_json(
        root / AUTHORIZATION_NAME, "Phase 41 explicit authorization"
    )
    prepared_sha = _sha256(prepared_bytes)
    authorization_sha = _sha256(authorization_bytes)
    prepared_precommit = prepared["deployment_fit_precommit"]
    assert isinstance(prepared_precommit, dict)
    precommit = _validate_authorization(
        authorization,
        prepared_sha256=prepared_sha,
        phase40_authorities_sha256=_phase40_authorities_sha256(prepared),
        prepared_deployment_fit_precommit=prepared_precommit,
    )
    if identity.path != _normalize_reserved_path_without_io(identity.path):
        raise ContractError("reserved path lexical authority drifted before claim")
    materialization = _load_materialization_receipt(root)
    if materialization is None:
        raise ContractError("the protected launcher materialization receipt is required")
    precommit_sha = _sha256(_canonical_json_bytes(precommit))
    global_claim = _global_claim_path(identity)
    _assert_unspent_and_clean(root, global_claim)
    preclaim_guard()
    _, claim_bytes = _claim_once(
        root,
        identity=identity,
        prepared_sha256=prepared_sha,
        authorization_sha256=authorization_sha,
        materialization_receipt_sha256=_sha256(materialization[1]),
        deployment_fit_precommit_sha256=precommit_sha,
        claimed_at_utc=clock(),
        clock=clock,
    )
    claim_sha = _sha256(claim_bytes)
    stage = "open_reserved_split"
    try:
        # Recheck the authority bytes after the durable claim and before the
        # sole opener, closing the mutation window without making a data read.
        if (root / PREPARED_NAME).read_bytes() != prepared_bytes:
            raise ContractError("prepared request changed after the durable claim")
        if (root / AUTHORIZATION_NAME).read_bytes() != authorization_bytes:
            raise ContractError("authorization changed after the durable claim")
        loaded = _open_snapshot_once(identity, opener)

        stage = "qwen_prediction"
        qwen_predictions = _validated_predictions(
            qwen_predictor(loaded.predictor_view),
            loaded.predictor_view,
            role="qwen",
        )
        stage = "phobert_prediction"
        phobert_predictions = _validated_predictions(
            phobert_predictor(loaded.predictor_view),
            loaded.predictor_view,
            role="phobert",
        )
        gold = tuple(row.gold_label for row in loaded.rows)
        qwen_metrics = compute_metrics(gold, qwen_predictions)
        phobert_metrics = compute_metrics(gold, phobert_predictions)
        statements = comparison_statements(qwen_metrics, phobert_metrics)

        stage = "freeze_outputs"
        qwen_bytes = _prediction_jsonl(
            "qwen", models[0].run_id, loaded.rows, qwen_predictions
        )
        phobert_bytes = _prediction_jsonl(
            "phobert", models[1].run_id, loaded.rows, phobert_predictions
        )
        _exclusive_write(root / QWEN_PREDICTIONS_NAME, qwen_bytes)
        _exclusive_write(root / PHOBERT_PREDICTIONS_NAME, phobert_bytes)
        result: dict[str, object] = {
            "schema_version": "phase41-one-shot-results-v1",
            "status": "completed",
            "prepared_sha256": prepared_sha,
            "authorization_sha256": authorization_sha,
            "claim_sha256": claim_sha,
            "held_out": {
                "records": len(loaded.rows),
                "bytes": loaded.payload_bytes,
                "sha256": identity.sha256,
            },
            "prior_exposure": {
                "human_content_exposure_disclosed": prepared["authorities"].get(
                    "prior_human_exposure_disclosed", False
                ),
                "claim": "one_post_freeze_model_evaluation_pass",
            },
            "models": [
                {
                    "role": models[0].role,
                    "run_id": models[0].run_id,
                    "artifact_sha256": models[0].artifact_sha256,
                    "selected_checkpoint_identity": models[0].selected_checkpoint_identity,
                    "predictions_sha256": _sha256(qwen_bytes),
                    "metrics": qwen_metrics,
                },
                {
                    "role": models[1].role,
                    "run_id": models[1].run_id,
                    "artifact_sha256": models[1].artifact_sha256,
                    "selected_checkpoint_identity": models[1].selected_checkpoint_identity,
                    "predictions_sha256": _sha256(phobert_bytes),
                    "metrics": phobert_metrics,
                },
            ],
            "comparison_statements": list(statements),
            "terminal_policy": {
                "rerun_permitted": False,
                "test_driven_training_action_permitted": False,
                "test_driven_checkpoint_selection_permitted": False,
                "test_driven_dataset_repair_permitted": False,
                "test_driven_contingency_activation_permitted": False,
            },
        }
        result_bytes = _canonical_json_bytes(result)
        report_bytes = _render_report(result)
        _exclusive_write(root / RESULTS_NAME, result_bytes)
        _exclusive_write(root / REPORT_NAME, report_bytes)
        stage = "freeze_completion_evidence"
        completion_writer(
            _CompletionProducts(
                result=result,
                identity=identity,
                prepared=prepared,
                models=models,
                claim_bytes=claim_bytes,
                qwen_predictions_bytes=qwen_bytes,
                phobert_predictions_bytes=phobert_bytes,
                results_bytes=result_bytes,
                report_bytes=report_bytes,
            )
        )
        return result
    except BaseException as exc:
        _terminal_failure(root, claim_sha, stage, exc, clock)
        raise


def _load_prediction_rows(
    path: Path, *, expected_role: str, expected_run_id: str
) -> tuple[list[str], list[str], tuple[Prediction, ...], bytes]:
    if not path.is_file() or path.is_symlink():
        raise ContractError(f"{expected_role} prediction artifact is missing or unsafe")
    payload = path.read_bytes()
    if not payload or not payload.endswith(b"\n"):
        raise ContractError(f"{expected_role} prediction artifact is partial or empty")
    gold: list[str] = []
    source_hashes: list[str] = []
    predictions: list[Prediction] = []
    for index, line in enumerate(payload.splitlines(keepends=True)):
        value = _parse_json_bytes(line, f"{expected_role} prediction row {index}")
        if line != _canonical_json_bytes(value):
            raise ContractError(f"{expected_role} prediction row is not canonical")
        expected_keys = {
            "schema_version",
            "model_role",
            "model_run_id",
            "row_id",
            "sequence_index",
            "source_row_sha256",
            "gold_label",
            "predicted_state",
            "raw_output_bytes",
            "raw_output_sha256",
            "parser_error",
        }
        if set(value) != expected_keys:
            raise ContractError(f"{expected_role} prediction fields drifted")
        if (
            value["schema_version"] != "phase41-prediction-row-v1"
            or value["model_role"] != expected_role
            or value["model_run_id"] != expected_run_id
            or value["sequence_index"] != index
        ):
            raise ContractError(f"{expected_role} prediction provenance/order drifted")
        _require_sha256(value["source_row_sha256"], "prediction source row")
        _require_sha256(value["raw_output_sha256"], "prediction raw output")
        if (
            not isinstance(value["raw_output_bytes"], int)
            or isinstance(value["raw_output_bytes"], bool)
            or value["raw_output_bytes"] < 0
        ):
            raise ContractError("prediction raw-output byte count is invalid")
        if value["gold_label"] not in LABEL_ORDER:
            raise ContractError("prediction gold label is outside the fixed order")
        gold.append(value["gold_label"])
        source_hashes.append(value["source_row_sha256"])
        predictions.append(
            Prediction(
                row_id=value["row_id"],
                predicted_state=value["predicted_state"],
                # verify_only needs the parsed state, not the sensitive raw
                # output. Its retained hash/length remain terminal evidence.
                raw_output="",
                parser_error=value["parser_error"],
            )
        )
    return gold, source_hashes, tuple(predictions), payload


def verify_only(output_root: Path) -> dict[str, object]:
    """Verify frozen results without accepting an opener or loading a model."""

    root = Path(output_root)
    prepared, prepared_bytes = _load_canonical_json(
        root / PREPARED_NAME, "Phase 41 evaluation request"
    )
    identity, models = _validate_prepared(prepared)
    _require_canonical_production_authorities(prepared)
    authorization, authorization_bytes = _load_canonical_json(
        root / AUTHORIZATION_NAME, "Phase 41 explicit authorization"
    )
    prepared_sha = _sha256(prepared_bytes)
    authorization_sha = _sha256(authorization_bytes)
    prepared_precommit = prepared["deployment_fit_precommit"]
    assert isinstance(prepared_precommit, dict)
    effective_precommit = _validate_authorization(
        authorization,
        prepared_sha256=prepared_sha,
        phase40_authorities_sha256=_phase40_authorities_sha256(prepared),
        prepared_deployment_fit_precommit=prepared_precommit,
    )
    _validate_claim_registry_root(_claim_registry_root())
    claim, claim_bytes = _load_canonical_json(root / CLAIM_NAME, "Phase 41 claim")
    global_claim, global_claim_bytes = _load_canonical_json(
        _global_claim_path(identity), "Phase 41 machine-local global claim"
    )
    if global_claim != claim or global_claim_bytes != claim_bytes:
        raise ContractError("local and global one-shot claims differ")
    if set(claim) != {
        "schema_version",
        "state",
        "claimed_at_utc",
        "prepared_sha256",
        "authorization_sha256",
        "execution_materialization_receipt_sha256",
        "deployment_fit_precommit_sha256",
        "reserved_split_sha256",
        "reserved_split_path_sha256",
        "claim_registry_sha256",
        "operator_sid",
        "meaning",
    } or (
        claim["schema_version"] != "phase41-one-shot-claim-v1"
        or claim["state"] != "spent"
        or not isinstance(claim["claimed_at_utc"], str)
        or not claim["claimed_at_utc"]
        or claim["prepared_sha256"] != prepared_sha
        or claim["authorization_sha256"] != authorization_sha
        or claim["execution_materialization_receipt_sha256"]
        != _sha256(
            _load_canonical_json(
                root / MATERIALIZATION_RECEIPT_NAME,
                "Phase 41 execution materialization receipt",
            )[1]
        )
        or claim["deployment_fit_precommit_sha256"]
        != _sha256(_canonical_json_bytes(effective_precommit))
        or claim["reserved_split_sha256"] != identity.sha256
        or claim["reserved_split_path_sha256"]
        != _sha256(identity.path.encode("utf-8"))
        or claim["claim_registry_sha256"]
        != _sha256(os.fspath(_claim_registry_root()).encode("utf-8"))
        or not isinstance(claim["operator_sid"], str)
        or not claim["operator_sid"]
        or claim["meaning"]
        != "existence permanently blocks another governed evaluation attempt"
    ):
        raise ContractError("durable claim differs from its authorities")
    claim_sha = _sha256(claim_bytes)
    terminal, _ = _load_canonical_json(root / TERMINAL_NAME, "Phase 41 terminal record")
    if set(terminal) != {
        "schema_version",
        "status",
        "completed_at_utc",
        "claim_sha256",
        "evidence_manifest_sha256",
        "access_receipt_sha256",
        "results_sha256",
        "report_sha256",
        "qwen_predictions_sha256",
        "phobert_predictions_sha256",
        "rerun_permitted",
    } or (
        terminal["schema_version"] != "phase41-terminal-v1"
        or terminal["status"] != "completed"
        or not isinstance(terminal["completed_at_utc"], str)
        or not terminal["completed_at_utc"]
        or terminal["claim_sha256"] != claim_sha
        or not SHA256_RE.fullmatch(str(terminal["evidence_manifest_sha256"]))
        or not SHA256_RE.fullmatch(str(terminal["access_receipt_sha256"]))
        or terminal["rerun_permitted"] is not False
    ):
        raise ContractError("Phase 41 evaluation is not terminal-complete")

    q_gold, q_sources, q_predictions, q_bytes = _load_prediction_rows(
        root / QWEN_PREDICTIONS_NAME,
        expected_role="qwen",
        expected_run_id=models[0].run_id,
    )
    p_gold, p_sources, p_predictions, p_bytes = _load_prediction_rows(
        root / PHOBERT_PREDICTIONS_NAME,
        expected_role="phobert",
        expected_run_id=models[1].run_id,
    )
    if (
        q_gold != p_gold
        or q_sources != p_sources
        or tuple(row.row_id for row in q_predictions)
        != tuple(row.row_id for row in p_predictions)
        or len(q_gold) != identity.records
    ):
        raise ContractError("the two prediction artifacts do not share one frozen cohort")
    retained_support = {label: q_gold.count(label) for label in LABEL_ORDER}
    if retained_support != dict(identity.label_counts):
        raise ContractError("retained prediction gold-label support differs from authority")
    if terminal.get("qwen_predictions_sha256") != _sha256(q_bytes) or terminal.get(
        "phobert_predictions_sha256"
    ) != _sha256(p_bytes):
        raise ContractError("prediction artifact hash differs from terminal evidence")

    result, result_bytes = _load_canonical_json(root / RESULTS_NAME, "Phase 41 results")
    if terminal.get("results_sha256") != _sha256(result_bytes):
        raise ContractError("result hash differs from terminal evidence")
    if set(result) != {
        "schema_version",
        "status",
        "prepared_sha256",
        "authorization_sha256",
        "claim_sha256",
        "held_out",
        "prior_exposure",
        "models",
        "comparison_statements",
        "terminal_policy",
    } or (
        result["schema_version"] != "phase41-one-shot-results-v1"
        or result["status"] != "completed"
        or result["prepared_sha256"] != prepared_sha
        or result["authorization_sha256"] != authorization_sha
        or result["claim_sha256"] != claim_sha
    ):
        raise ContractError("result authority fields drifted")
    if result["held_out"] != {
        "records": identity.records,
        "bytes": identity.bytes,
        "sha256": identity.sha256,
    }:
        raise ContractError("result held-out identity drifted")
    if result["prior_exposure"] != {
        "human_content_exposure_disclosed": True,
        "claim": "one_post_freeze_model_evaluation_pass",
    }:
        raise ContractError("prior-exposure disclosure drifted")
    result_models = result.get("models")
    if not isinstance(result_models, list) or len(result_models) != 2:
        raise ContractError("results must contain exactly two model rows")
    q_metrics = compute_metrics(q_gold, q_predictions)
    p_metrics = compute_metrics(p_gold, p_predictions)
    expected_metrics = (q_metrics, p_metrics)
    for model, expected_identity, expected_metric, predictions_sha in zip(
        result_models,
        models,
        expected_metrics,
        (_sha256(q_bytes), _sha256(p_bytes)),
        strict=True,
    ):
        if not isinstance(model, dict):
            raise ContractError("result model row is malformed")
        if set(model) != {
            "role",
            "run_id",
            "artifact_sha256",
            "selected_checkpoint_identity",
            "predictions_sha256",
            "metrics",
        } or (
            model["role"] != expected_identity.role
            or model["run_id"] != expected_identity.run_id
            or model["artifact_sha256"] != expected_identity.artifact_sha256
            or model["selected_checkpoint_identity"]
            != expected_identity.selected_checkpoint_identity
            or model["predictions_sha256"] != predictions_sha
            or model["metrics"] != expected_metric
        ):
            raise ContractError("result model identity or metrics drifted")
    expected_statements = list(comparison_statements(q_metrics, p_metrics))
    if result.get("comparison_statements") != expected_statements:
        raise ContractError("plain comparison statements drifted")
    if result.get("terminal_policy") != {
        "rerun_permitted": False,
        "test_driven_training_action_permitted": False,
        "test_driven_checkpoint_selection_permitted": False,
        "test_driven_dataset_repair_permitted": False,
        "test_driven_contingency_activation_permitted": False,
    }:
        raise ContractError("terminal result policy drifted")
    report_path = root / REPORT_NAME
    if not report_path.is_file() or report_path.is_symlink():
        raise ContractError("Phase 41 Markdown report is missing or unsafe")
    report_bytes = report_path.read_bytes()
    if terminal.get("report_sha256") != _sha256(report_bytes):
        raise ContractError("report hash differs from terminal evidence")
    if report_bytes != _render_report(result):
        raise ContractError("Markdown report differs from the canonical result")
    return result


def _local_module_path(repository_root: Path, module: str) -> Path | None:
    relative = Path(*module.split("."))
    module_path = repository_root / relative.with_suffix(".py")
    package_path = repository_root / relative / "__init__.py"
    if module_path.is_file():
        return module_path
    if package_path.is_file():
        return package_path
    return None


def _phase41_source_import_closure(repository_root: Path) -> tuple[str, ...]:
    """Return the exact repository-Python closure reachable from the fixed CLI.

    The shared CLI has eager imports for older commands, so those modules are
    part of the executable startup surface even though the launcher fixes the
    selected verb.  Inventorying the real transitive closure is safer than
    claiming that only the three Phase 41 files can execute.
    """

    pending = list(_PHASE41_ENTRY_MODULES)
    visited: set[str] = set()
    relative_paths: set[str] = set()

    def enqueue(module: str) -> None:
        if module.startswith("src") and module not in visited and module not in pending:
            pending.append(module)

    while pending:
        module = pending.pop()
        if module in visited:
            continue
        visited.add(module)
        path = _local_module_path(repository_root, module)
        if path is None:
            continue
        relative_paths.add(path.relative_to(repository_root).as_posix())
        parts = module.split(".")
        for end in range(1, len(parts)):
            enqueue(".".join(parts[:end]))
        try:
            tree = ast.parse(path.read_text(encoding="utf-8", errors="strict"))
        except (OSError, UnicodeError, SyntaxError) as exc:
            raise ContractError(f"execution source cannot be parsed: {path}") from exc
        package_parts = parts if path.name == "__init__.py" else parts[:-1]
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    enqueue(alias.name)
            elif isinstance(node, ast.ImportFrom):
                if node.level:
                    keep = len(package_parts) - node.level + 1
                    if keep < 0:
                        raise ContractError("execution source has an invalid relative import")
                    base_parts = package_parts[:keep]
                    if node.module:
                        base_parts.extend(node.module.split("."))
                    base = ".".join(base_parts)
                else:
                    base = node.module or ""
                if base:
                    enqueue(base)
                    for alias in node.names:
                        if alias.name != "*":
                            candidate = f"{base}.{alias.name}"
                            if _local_module_path(repository_root, candidate) is not None:
                                enqueue(candidate)
    return tuple(sorted(relative_paths))


def _python_runtime_authority() -> dict[str, object]:
    executable = Path(sys.executable)
    if not executable.is_absolute() or not executable.is_file() or executable.is_symlink():
        raise ContractError("Phase 41 Python executable is missing or unsafe")
    executable_bytes = executable.read_bytes()
    import_roots: list[str] = []
    for key in ("purelib", "platlib"):
        raw = sysconfig.get_paths().get(key)
        if not raw:
            continue
        candidate = Path(os.path.abspath(os.path.normpath(raw)))
        if not candidate.is_dir() or candidate.is_symlink():
            raise ContractError("Phase 41 runtime import root is missing or unsafe")
        rendered = os.fspath(candidate)
        if rendered not in import_roots:
            import_roots.append(rendered)
    if not import_roots:
        raise ContractError("Phase 41 runtime import roots are unavailable")
    return {
        "path": os.fspath(executable),
        "bytes": len(executable_bytes),
        "sha256": _sha256(executable_bytes),
        "version": platform.python_version(),
        "runtime_import_roots": import_roots,
    }


def _write_source_manifest(
    output_root: Path,
    declared_tree_sha256: str,
    *,
    preparation_scope: str,
    repository_root: Path | None = None,
    comparison_launch_receipt_sha256: str | None = None,
) -> tuple[Path, str]:
    _require_sha256(declared_tree_sha256, "execution source tree")
    if preparation_scope == SYNTHETIC_PREPARATION_SCOPE:
        if _TEST_RUNTIME.get() is None:
            raise ContractError("synthetic source materialization is unavailable")
        repository = Path(__file__).resolve().parents[2]
    elif preparation_scope == PRODUCTION_PREPARATION_SCOPE:
        if _TEST_RUNTIME.get() is not None or repository_root is None:
            raise ContractError("production source materialization is unavailable")
        repository = Path(
            os.path.abspath(os.path.normpath(os.fspath(repository_root)))
        )
        code_root = Path(__file__).resolve().parents[2]
        if os.path.normcase(os.fspath(repository)) != os.path.normcase(
            os.fspath(code_root)
        ):
            raise ContractError("production source root differs from the running checkout")
    else:
        raise ContractError(
            "execution source preparation scope is invalid"
        )
    relative_files = _phase41_source_import_closure(repository)
    inventory: list[dict[str, object]] = []
    for relative in relative_files:
        candidate = repository / relative
        if not candidate.is_file() or candidate.is_symlink():
            raise ContractError(f"execution source is missing or unsafe: {relative}")
        content = candidate.read_bytes()
        inventory.append(
            {"path": relative, "bytes": len(content), "sha256": _sha256(content)}
        )
    launcher_relative = "scripts/phase41_one_shot_launcher.ps1"
    launcher_path = repository / launcher_relative
    if not launcher_path.is_file() or launcher_path.is_symlink():
        raise ContractError("Phase 41 launcher is missing or unsafe")
    launcher_bytes = launcher_path.read_bytes()
    launcher_host_extra: dict[str, object] = {}
    if preparation_scope == PRODUCTION_PREPARATION_SCOPE:
        from src.model_adaptation.phase40_comparison_launch import (
            verify_phase40_comparison_launch_receipt,
        )

        external_receipt = verify_phase40_comparison_launch_receipt(
            repo_root=repository
        )
        external_receipt_sha = _require_sha256(
            external_receipt.get("receipt_sha256"),
            "external comparison-launch receipt",
        )
        if external_receipt_sha != comparison_launch_receipt_sha256:
            raise ContractError("external comparison-launch authority drifted")
        external_host = external_receipt.get("launcher_host")
        if not isinstance(external_host, Mapping):
            raise ContractError("external comparison launcher host is malformed")
        launcher_host_path = Path(r"C:\Program Files\PowerShell\7\pwsh.exe")
        launcher_host_extra = {
            "external_launch_receipt_sha256": external_receipt_sha
        }
    else:
        external_host = None
        launcher_host_path = Path(sys.executable)
    if (
        not launcher_host_path.is_absolute()
        or not launcher_host_path.is_file()
        or launcher_host_path.is_symlink()
    ):
        raise ContractError("synthetic launcher host is missing or unsafe")
    launcher_host_bytes = launcher_host_path.read_bytes()
    if external_host is not None and (
        external_host.get("bytes") != len(launcher_host_bytes)
        or external_host.get("sha256") != _sha256(launcher_host_bytes)
    ):
        raise ContractError("external comparison launcher host bytes drifted")
    source_tree_sha256 = _sha256(
        b"phase41-execution-source-tree-v1\0" + _canonical_json_bytes(inventory)
    )
    payload = _canonical_json_bytes(
        {
            "schema_version": "phase41-execution-source-manifest-v1",
            "preparation_scope": preparation_scope,
            "upstream_declared_source_tree_sha256": declared_tree_sha256,
            "source_tree_sha256": source_tree_sha256,
            "files": inventory,
            "launcher": {
                "path": launcher_relative,
                "bytes": len(launcher_bytes),
                "sha256": _sha256(launcher_bytes),
            },
            "launcher_host": {
                "mode": (
                    SYNTHETIC_PREPARATION_SCOPE
                    if preparation_scope == SYNTHETIC_PREPARATION_SCOPE
                    else "phase40_external_launcher_authority"
                ),
                "path": os.fspath(launcher_host_path),
                "bytes": len(launcher_host_bytes),
                "sha256": _sha256(launcher_host_bytes),
                **launcher_host_extra,
            },
            "python": _python_runtime_authority(),
            "closed_import_roots": [
                *_PHASE41_ENTRY_MODULES,
            ],
            "alternate_evaluators_permitted": False,
        }
    )
    path = _exclusive_write(Path(output_root) / SOURCE_MANIFEST_NAME, payload)
    return path, _sha256(payload)


def _normalized_path_sha256(path: Path) -> str:
    normalized = os.path.normcase(
        os.path.abspath(os.path.normpath(os.fspath(path)))
    )
    return _sha256(normalized.encode("utf-8"))


def _materialization_payload(
    *,
    mode: str,
    root: Path,
    source: Mapping[str, object],
    source_bytes: bytes,
    protocols_sha256: str,
    model_bundle_authorities_sha256: str,
    phase40_authority_hashes: Mapping[str, object],
    created_at_utc: str,
    launcher_capability_sha256: str | None = None,
    launcher_process_id: int | None = None,
    launcher_process_image_path_sha256: str | None = None,
    launcher_process_image_sha256: str | None = None,
) -> bytes:
    if mode not in {"locked-clean-runtime", "synthetic-test"}:
        raise ContractError("execution materialization mode is invalid")
    required_authorities = _required_phase40_authority_hashes(
        phase40_authority_hashes
    )
    launcher = source.get("launcher")
    launcher_host = source.get("launcher_host")
    python_authority = source.get("python")
    files = source.get("files")
    if (
        not isinstance(launcher, dict)
        or not isinstance(launcher_host, dict)
        or not isinstance(python_authority, dict)
        or not isinstance(files, list)
    ):
        raise ContractError("execution materialization authorities are incomplete")
    if mode == "synthetic-test":
        if (
            source.get("preparation_scope") != SYNTHETIC_PREPARATION_SCOPE
            or launcher_host.get("mode") != SYNTHETIC_PREPARATION_SCOPE
        ):
            raise ContractError("synthetic materialization scope drifted")
        capability_sha256 = "0" * 64
        process_id = 0
        process_image_path_sha256 = "0" * 64
        process_image_sha256 = "0" * 64
        external_launcher_authority_sha256 = "0" * 64
    else:
        if (
            source.get("preparation_scope") != PRODUCTION_PREPARATION_SCOPE
            or launcher_host.get("mode")
            != "phase40_external_launcher_authority"
            or not isinstance(launcher_host.get("path"), str)
            or not Path(str(launcher_host["path"])).is_absolute()
        ):
            raise ContractError("production launcher host authority is absent")
        external_launcher_authority_sha256 = _require_sha256(
            launcher_host.get("external_launch_receipt_sha256"),
            "external Phase 40 launcher authority",
        )
        capability_sha256 = _require_sha256(
            launcher_capability_sha256, "live launcher capability"
        )
        if (
            not isinstance(launcher_process_id, int)
            or isinstance(launcher_process_id, bool)
            or launcher_process_id <= 0
        ):
            raise ContractError("live launcher process ID is invalid")
        process_id = launcher_process_id
        process_image_path_sha256 = _require_sha256(
            launcher_process_image_path_sha256, "launcher process image path"
        )
        process_image_sha256 = _require_sha256(
            launcher_process_image_sha256, "launcher process image"
        )
        if (
            process_image_path_sha256
            != _normalized_path_sha256(Path(str(launcher_host["path"])))
            or process_image_sha256 != launcher_host.get("sha256")
        ):
            raise ContractError("launcher process differs from its precommitted host authority")
    return _canonical_json_bytes(
        {
            "schema_version": "phase41-execution-materialization-v1",
            "mode": mode,
            "preparation_scope": source.get("preparation_scope"),
            "created_at_utc": created_at_utc,
            "source_manifest_sha256": _sha256(source_bytes),
            "source_tree_sha256": source["source_tree_sha256"],
            "protocols_sha256": protocols_sha256,
            "model_bundle_authorities_sha256": model_bundle_authorities_sha256,
            **required_authorities,
            "launcher_sha256": launcher["sha256"],
            "launcher_host_sha256": launcher_host["sha256"],
            "external_launcher_authority_sha256": external_launcher_authority_sha256,
            "python_executable_sha256": python_authority["sha256"],
            "clean_runtime_root_sha256": _normalized_path_sha256(root),
            "source_file_count": len(files),
            "source_handles_locked_at_launch": True,
            "launcher_capability_sha256": capability_sha256,
            "launcher_process_id": process_id,
            "launcher_process_image_path_sha256": process_image_path_sha256,
            "launcher_process_image_sha256": process_image_sha256,
            "runtime_import_roots": python_authority["runtime_import_roots"],
        }
    )


def _load_materialization_receipt(
    output_root: Path,
) -> tuple[dict[str, object], bytes] | None:
    path = Path(output_root) / MATERIALIZATION_RECEIPT_NAME
    if not path.exists() and not path.is_symlink():
        return None
    return _load_canonical_json(path, "Phase 41 execution materialization receipt")


def _materialized_source_root(
    output_root: Path, receipt: Mapping[str, object] | None
) -> Path:
    if receipt is None:
        return Path(__file__).resolve().parents[2]
    mode = receipt.get("mode")
    if mode == "locked-clean-runtime":
        return Path(output_root) / "clean-runtime"
    if mode == "synthetic-test" and _TEST_RUNTIME.get() is not None:
        return Path(__file__).resolve().parents[2]
    raise ContractError("execution materialization mode is not permitted")


def _verify_materialization_receipt(
    *,
    receipt: Mapping[str, object],
    receipt_bytes: bytes,
    source_root: Path,
    source: Mapping[str, object],
    source_bytes: bytes,
    protocols_sha256: str,
    model_bundle_authorities_sha256: str,
    phase40_authority_hashes: Mapping[str, object],
) -> None:
    expected_fields = {
        "schema_version",
        "mode",
        "preparation_scope",
        "created_at_utc",
        "source_manifest_sha256",
        "source_tree_sha256",
        "protocols_sha256",
        "model_bundle_authorities_sha256",
        *_PHASE40_REQUIRED_AUTHORITY_HASH_FIELDS,
        "launcher_sha256",
        "launcher_host_sha256",
        "external_launcher_authority_sha256",
        "python_executable_sha256",
        "clean_runtime_root_sha256",
        "source_file_count",
        "source_handles_locked_at_launch",
        "launcher_capability_sha256",
        "launcher_process_id",
        "launcher_process_image_path_sha256",
        "launcher_process_image_sha256",
        "runtime_import_roots",
    }
    launcher = source.get("launcher")
    launcher_host = source.get("launcher_host")
    python_authority = source.get("python")
    files = source.get("files")
    if (
        set(receipt) != expected_fields
        or receipt["schema_version"] != "phase41-execution-materialization-v1"
        or receipt["mode"] not in {"locked-clean-runtime", "synthetic-test"}
        or not isinstance(receipt["created_at_utc"], str)
        or not receipt["created_at_utc"]
        or not isinstance(launcher, dict)
        or not isinstance(launcher_host, dict)
        or not isinstance(python_authority, dict)
        or not isinstance(files, list)
        or receipt["source_manifest_sha256"] != _sha256(source_bytes)
        or receipt["source_tree_sha256"] != source.get("source_tree_sha256")
        or receipt["protocols_sha256"] != protocols_sha256
        or receipt["model_bundle_authorities_sha256"]
        != model_bundle_authorities_sha256
        or any(
            receipt[name]
            != _required_phase40_authority_hashes(phase40_authority_hashes)[name]
            for name in _PHASE40_REQUIRED_AUTHORITY_HASH_FIELDS
        )
        or receipt["launcher_sha256"] != launcher.get("sha256")
        or receipt["launcher_host_sha256"] != launcher_host.get("sha256")
        or receipt["preparation_scope"] != source.get("preparation_scope")
        or receipt["python_executable_sha256"] != python_authority.get("sha256")
        or receipt["clean_runtime_root_sha256"]
        != _normalized_path_sha256(source_root)
        or receipt["source_file_count"] != len(files)
        or receipt["source_handles_locked_at_launch"] is not True
        or not isinstance(receipt["launcher_capability_sha256"], str)
        or not SHA256_RE.fullmatch(receipt["launcher_capability_sha256"])
        or not isinstance(receipt["launcher_process_id"], int)
        or isinstance(receipt["launcher_process_id"], bool)
        or not isinstance(receipt["launcher_process_image_path_sha256"], str)
        or not SHA256_RE.fullmatch(
            receipt["launcher_process_image_path_sha256"]
        )
        or not isinstance(receipt["launcher_process_image_sha256"], str)
        or not SHA256_RE.fullmatch(receipt["launcher_process_image_sha256"])
        or (
            receipt["mode"] == "synthetic-test"
            and (
                receipt["external_launcher_authority_sha256"] != "0" * 64
                or receipt["launcher_capability_sha256"] != "0" * 64
                or receipt["launcher_process_id"] != 0
                or receipt["launcher_process_image_path_sha256"] != "0" * 64
                or receipt["launcher_process_image_sha256"] != "0" * 64
            )
        )
        or (
            receipt["mode"] == "locked-clean-runtime"
            and (
                receipt["preparation_scope"] != PRODUCTION_PREPARATION_SCOPE
                or launcher_host.get("mode")
                != "phase40_external_launcher_authority"
                or receipt["external_launcher_authority_sha256"]
                != launcher_host.get("external_launch_receipt_sha256")
                or receipt["launcher_capability_sha256"] == "0" * 64
                or receipt["launcher_process_id"] <= 0
                or receipt["launcher_process_image_path_sha256"] == "0" * 64
                or receipt["launcher_process_image_sha256"] == "0" * 64
                or receipt["launcher_process_image_path_sha256"]
                != _normalized_path_sha256(Path(str(launcher_host.get("path", ""))))
                or receipt["launcher_process_image_sha256"]
                != launcher_host.get("sha256")
            )
        )
        or receipt["runtime_import_roots"]
        != python_authority.get("runtime_import_roots")
        or receipt_bytes
        != _materialization_payload(
            mode=str(receipt["mode"]),
            root=source_root,
            source=source,
            source_bytes=source_bytes,
            protocols_sha256=protocols_sha256,
            model_bundle_authorities_sha256=model_bundle_authorities_sha256,
            phase40_authority_hashes=phase40_authority_hashes,
            created_at_utc=str(receipt["created_at_utc"]),
            launcher_capability_sha256=str(
                receipt["launcher_capability_sha256"]
            ),
            launcher_process_id=int(receipt["launcher_process_id"]),
            launcher_process_image_path_sha256=str(
                receipt["launcher_process_image_path_sha256"]
            ),
            launcher_process_image_sha256=str(
                receipt["launcher_process_image_sha256"]
            ),
        )
    ):
        raise ContractError("execution materialization receipt drifted")


def _acquire_live_launcher_capability(output_root: Path) -> _LiveLauncherCapability:
    """Read and bind the one-use nonce from the inherited Windows stdin pipe."""

    if _TEST_RUNTIME.get() is not None or os.name != "nt":
        raise ContractError("production run requires a Windows launcher capability")
    root = Path(output_root)
    request, _ = _load_canonical_json(root / PREPARED_NAME, "Phase 41 request")
    _validate_prepared(request)
    _require_canonical_production_authorities(request)
    materialization = _load_materialization_receipt(output_root)
    if materialization is None:
        raise ContractError("the protected launcher materialization receipt is required")
    receipt, _ = materialization
    if receipt.get("mode") != "locked-clean-runtime":
        raise ContractError("production run requires locked clean-runtime materialization")
    source, _ = _load_canonical_json(
        root / SOURCE_MANIFEST_NAME, "Phase 41 execution source manifest"
    )
    launcher_host = source.get("launcher_host")
    if (
        source.get("preparation_scope") != PRODUCTION_PREPARATION_SCOPE
        or request.get("preparation_scope") != PRODUCTION_PREPARATION_SCOPE
        or not isinstance(launcher_host, dict)
        or launcher_host.get("mode")
        != "phase40_external_launcher_authority"
        or not isinstance(launcher_host.get("path"), str)
        or launcher_host.get("external_launch_receipt_sha256")
        != request.get("authorities", {}).get("comparison_launch_receipt_sha256")
        or receipt.get("external_launcher_authority_sha256")
        != launcher_host.get("external_launch_receipt_sha256")
        or receipt.get("launcher_host_sha256") != launcher_host.get("sha256")
        or receipt.get("launcher_process_image_path_sha256")
        != _normalized_path_sha256(Path(str(launcher_host.get("path", ""))))
        or receipt.get("launcher_process_image_sha256")
        != launcher_host.get("sha256")
    ):
        raise ContractError("launcher parent differs from the precommitted source authority")
    launcher_process_id = receipt.get("launcher_process_id")
    if (
        not isinstance(launcher_process_id, int)
        or isinstance(launcher_process_id, bool)
        or launcher_process_id <= 0
    ):
        raise ContractError("launcher process identity is invalid")
    for field, description in (
        ("launcher_capability_sha256", "launcher capability"),
        ("launcher_process_image_path_sha256", "launcher process image path"),
        ("launcher_process_image_sha256", "launcher process image"),
    ):
        _require_sha256(receipt.get(field), description)

    import ctypes
    from ctypes import wintypes
    import msvcrt

    FILE_TYPE_PIPE = 3
    STD_INPUT_HANDLE = 0xFFFFFFF6
    PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
    SYNCHRONIZE = 0x100000
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    try:
        descriptor = int(sys.stdin.buffer.fileno())
        pipe_handle = int(msvcrt.get_osfhandle(descriptor))
    except (AttributeError, OSError, TypeError, ValueError) as exc:
        raise ContractError(
            "production run requires the inherited launcher pipe on stdin"
        ) from exc
    kernel32.GetStdHandle.argtypes = [wintypes.DWORD]
    kernel32.GetStdHandle.restype = wintypes.HANDLE
    standard_handle = int(kernel32.GetStdHandle(STD_INPUT_HANDLE))
    get_file_type = kernel32.GetFileType
    get_file_type.argtypes = [wintypes.HANDLE]
    get_file_type.restype = wintypes.DWORD
    if (
        descriptor != 0
        or pipe_handle <= 0
        or pipe_handle != standard_handle
        or int(get_file_type(wintypes.HANDLE(pipe_handle))) != FILE_TYPE_PIPE
    ):
        raise ContractError("inherited launcher capability is not the stdin pipe")

    get_server_pid = kernel32.GetNamedPipeServerProcessId
    get_server_pid.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.ULONG)]
    get_server_pid.restype = wintypes.BOOL
    server_process_id = wintypes.ULONG()
    if not get_server_pid(
        wintypes.HANDLE(pipe_handle), ctypes.byref(server_process_id)
    ):
        raise ContractError("launcher pipe server identity is unavailable")
    if int(server_process_id.value) != launcher_process_id:
        raise ContractError("launcher pipe server differs from the frozen parent")

    open_process = kernel32.OpenProcess
    open_process.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    open_process.restype = wintypes.HANDLE
    process_handle = int(
        open_process(
            PROCESS_QUERY_LIMITED_INFORMATION | SYNCHRONIZE,
            False,
            server_process_id.value,
        )
    )
    if not process_handle:
        raise ContractError("launcher parent process cannot be inspected")
    try:
        query_image = kernel32.QueryFullProcessImageNameW
        query_image.argtypes = [
            wintypes.HANDLE,
            wintypes.DWORD,
            wintypes.LPWSTR,
            ctypes.POINTER(wintypes.DWORD),
        ]
        query_image.restype = wintypes.BOOL
        capacity = wintypes.DWORD(32768)
        image_buffer = ctypes.create_unicode_buffer(capacity.value)
        if not query_image(
            wintypes.HANDLE(process_handle),
            0,
            image_buffer,
            ctypes.byref(capacity),
        ):
            raise ContractError("launcher parent image path is unavailable")
        image_path = Path(image_buffer.value)
        if (
            _normalized_path_sha256(image_path)
            != receipt.get("launcher_process_image_path_sha256")
            or not image_path.is_file()
            or image_path.is_symlink()
            or _sha256(image_path.read_bytes())
            != receipt.get("launcher_process_image_sha256")
            or os.path.normcase(os.path.abspath(os.fspath(image_path)))
            != os.path.normcase(
                os.path.abspath(os.path.normpath(str(launcher_host["path"])))
            )
        ):
            raise ContractError("launcher parent image differs from its frozen authority")

        nonce = bytearray()
        while len(nonce) < 32:
            chunk = os.read(descriptor, 32 - len(nonce))
            if not chunk:
                raise ContractError("inherited launcher capability closed early")
            nonce.extend(chunk)
        nonce_sha256 = _sha256(bytes(nonce))
        if nonce_sha256 != receipt.get("launcher_capability_sha256"):
            raise ContractError("inherited launcher nonce differs from its receipt")
        capability = _LiveLauncherCapability(
            output_root_sha256=_normalized_path_sha256(Path(output_root)),
            pipe_handle=pipe_handle,
            launcher_process_handle=process_handle,
            launcher_process_id=int(server_process_id.value),
            launcher_capability_sha256=nonce_sha256,
            launcher_process_image_path_sha256=str(
                receipt["launcher_process_image_path_sha256"]
            ),
            launcher_process_image_sha256=str(
                receipt["launcher_process_image_sha256"]
            ),
        )
        capability.assert_live()
        return capability
    except BaseException:
        close_handle = kernel32.CloseHandle
        close_handle.argtypes = [wintypes.HANDLE]
        close_handle.restype = wintypes.BOOL
        close_handle(wintypes.HANDLE(process_handle))
        raise


def _require_live_launcher_capability(
    output_root: Path, *, consume: bool
) -> _LiveLauncherCapability | None:
    """Return only the currently OS-verified launcher capability."""

    if _TEST_RUNTIME.get() is not None:
        return None
    request, _ = _load_canonical_json(
        Path(output_root) / PREPARED_NAME, "Phase 41 request"
    )
    _validate_prepared(request)
    _require_canonical_production_authorities(request)
    capability = _LIVE_LAUNCHER_CAPABILITY.get()
    if type(capability) is not _LiveLauncherCapability:  # reject forged subclasses
        raise ContractError("production run lacks its internally owned launcher capability")
    materialization = _load_materialization_receipt(output_root)
    if materialization is None:
        raise ContractError("the protected launcher materialization receipt is required")
    receipt, _ = materialization
    if (
        capability.output_root_sha256 != _normalized_path_sha256(Path(output_root))
        or capability.launcher_process_id != receipt.get("launcher_process_id")
        or capability.launcher_capability_sha256
        != receipt.get("launcher_capability_sha256")
        or capability.launcher_process_image_path_sha256
        != receipt.get("launcher_process_image_path_sha256")
        or capability.launcher_process_image_sha256
        != receipt.get("launcher_process_image_sha256")
    ):
        raise ContractError("live inherited launcher capability differs from receipt")
    capability.assert_live()
    if consume:
        capability.consume_once()
    return capability


def _ensure_synthetic_materialization_receipt(output_root: Path) -> None:
    if _TEST_RUNTIME.get() is None:
        raise ContractError("the protected launcher materialization receipt is required")
    root = Path(output_root)
    existing = _load_materialization_receipt(root)
    if existing is not None:
        return
    source, source_bytes = _load_canonical_json(
        root / SOURCE_MANIFEST_NAME, "Phase 41 execution source manifest"
    )
    request, _ = _load_canonical_json(root / PREPARED_NAME, "Phase 41 request")
    _validate_prepared(request)
    _require_canonical_production_authorities(request)
    authorities = request["authorities"]
    assert isinstance(authorities, dict)
    payload = _materialization_payload(
        mode="synthetic-test",
        root=Path(__file__).resolve().parents[2],
        source=source,
        source_bytes=source_bytes,
        protocols_sha256=_sha256((root / PROTOCOLS_NAME).read_bytes()),
        model_bundle_authorities_sha256=_sha256(
            _canonical_json_bytes(authorities["model_bundle_authorities"])
        ),
        phase40_authority_hashes=authorities,
        created_at_utc=_utc_now(),
    )
    _exclusive_write(root / MATERIALIZATION_RECEIPT_NAME, payload)


def _prepare_phase41_synthetic_for_test(
    output_root: Path,
    *,
    held_out: OpaqueHeldOutAuthority,
    models: Sequence[FrozenModelIdentity],
    protocols,  # Phase41ProtocolAuthority; kept lazy to avoid a module cycle
    comparison_authority_sha256: str,
    review_closure_sha256: str,
    comparison_launch_receipt_sha256: str,
    execution_source_manifest_sha256: str,
    prior_human_exposure_disclosed: bool,
    deployment_fit_choice: str,
) -> PreparedPhase41Evaluation:
    """Freeze a durable synthetic-only fixture without touching ``held_out.path``."""

    if _TEST_RUNTIME.get() is None:
        raise ContractError("synthetic preparation is unavailable in production")

    from src.model_adaptation.phase41_protocols import (
        Phase41ProtocolAuthority,
        write_protocol_authority,
    )

    if not isinstance(held_out, SplitIdentity):
        raise ContractError("held-out authority must be OpaqueHeldOutAuthority")
    ordered_models = tuple(models)
    if len(ordered_models) != 2 or tuple(model.role for model in ordered_models) != (
        "qwen",
        "phobert",
    ):
        raise ContractError("model identities must be Qwen then PhoBERT")
    if not isinstance(protocols, Phase41ProtocolAuthority):
        raise ContractError("protocol authority type is invalid")
    if (
        protocols.qwen.body["adapter_checkpoint_identity"]
        != ordered_models[0].selected_checkpoint_identity
        or protocols.phobert.body["classifier_checkpoint_identity"]
        != ordered_models[1].selected_checkpoint_identity
        or protocols.qwen.body["adapter_sha256"]
        != ordered_models[0].artifact_sha256
        or protocols.phobert.body["classifier_state_sha256"]
        != ordered_models[1].artifact_sha256
    ):
        raise ContractError("protocol checkpoint/artifact identities differ from selected models")
    if prior_human_exposure_disclosed is not True:
        raise ContractError("prior human/content exposure disclosure is mandatory")

    root = Path(output_root)
    protocol_path = write_protocol_authority(root, protocols)
    protocol_bytes = protocol_path.read_bytes()
    _, source_manifest_sha = _write_source_manifest(
        root,
        execution_source_manifest_sha256,
        preparation_scope=SYNTHETIC_PREPARATION_SCOPE,
    )
    authorities = {
        "protocols_sha256": _sha256(protocol_bytes),
        "model_bundle_authorities": [
            {
                "role": protocol.role,
                "bundle_root": protocol.body["bundle_root"],
                "bundle_root_sha256": protocol.body["bundle_root_sha256"],
            }
            for protocol in (protocols.qwen, protocols.phobert)
        ],
        "execution_source_manifest_sha256": source_manifest_sha,
        "comparison_authority_sha256": _require_sha256(
            comparison_authority_sha256, "comparison authority"
        ),
        "review_closure_sha256": _require_sha256(review_closure_sha256, "review closure"),
        "comparison_launch_receipt_sha256": _require_sha256(
            comparison_launch_receipt_sha256, "comparison launch receipt"
        ),
        **_SYNTHETIC_REQUIRED_AUTHORITY_HASHES,
        "prior_human_exposure_disclosed": True,
    }
    request_path = prepare_evaluation(
        root,
        reserved_split_path=Path(held_out.path),
        expected_records=held_out.records,
        expected_bytes=held_out.bytes,
        expected_sha256=held_out.sha256,
        expected_label_counts=dict(held_out.label_counts),
        models=ordered_models,
        deployment_fit_choice=deployment_fit_choice,
        preparation_scope=SYNTHETIC_PREPARATION_SCOPE,
        authorities=authorities,
    )
    request_bytes = request_path.read_bytes()
    prepared_sha = _sha256(request_bytes)
    preauthorization = _canonical_json_bytes(
        {
            "schema_version": "phase41-preauthorization-receipt-v1",
            "state": "prepared",
            "prepared_sha256": prepared_sha,
            "protocols_sha256": authorities["protocols_sha256"],
            "model_bundle_authorities_sha256": _sha256(
                _canonical_json_bytes(authorities["model_bundle_authorities"])
            ),
            "execution_source_manifest_sha256": source_manifest_sha,
            "comparison_authority_sha256": authorities["comparison_authority_sha256"],
            "review_closure_sha256": authorities["review_closure_sha256"],
            "comparison_launch_receipt_sha256": authorities[
                "comparison_launch_receipt_sha256"
            ],
            **{
                name: authorities[name]
                for name in _PHASE40_REQUIRED_AUTHORITY_HASH_FIELDS
            },
            "models_ready_before_claim_required": True,
            "validation_contingency_closed_required": True,
        }
    )
    _exclusive_write(root / PREAUTHORIZATION_NAME, preauthorization)
    return PreparedPhase41Evaluation(request_path, prepared_sha)


def _production_preauthorization_record(
    *,
    request: Mapping[str, object],
    request_bytes: bytes,
    authorities: Mapping[str, object],
    model_smokes: Sequence[Mapping[str, object]],
    claim_registry: Mapping[str, object],
) -> dict[str, object]:
    return {
        "schema_version": "phase41-preauthorization-receipt-v2",
        "state": "prepared",
        "prepared_sha256": _sha256(request_bytes),
        "protocols_sha256": authorities["protocols_sha256"],
        "model_bundle_authorities_sha256": _sha256(
            _canonical_json_bytes(authorities["model_bundle_authorities"])
        ),
        "execution_source_manifest_sha256": authorities[
            "execution_source_manifest_sha256"
        ],
        "comparison_authority_sha256": authorities["comparison_authority_sha256"],
        "review_closure_sha256": authorities["review_closure_sha256"],
        "comparison_launch_receipt_sha256": authorities[
            "comparison_launch_receipt_sha256"
        ],
        **{
            name: authorities[name]
            for name in (
                *_PHASE40_REQUIRED_AUTHORITY_HASH_FIELDS,
                *_PRODUCTION_EXTRA_AUTHORITY_HASH_FIELDS,
            )
        },
        "models": request["models"],
        "opaque_held_out": request["held_out"],
        "deployment_fit_choice": PENDING_DEPLOYMENT_FIT_CHOICE,
        "model_smokes": [dict(item) for item in model_smokes],
        "claim_registry": dict(claim_registry),
        "models_ready_before_claim_required": True,
        "validation_contingency_closed_required": True,
        "reserved_split_access_attempted": False,
        "prior_human_exposure_disclosure": _PRIOR_HUMAN_EXPOSURE_DISCLOSURE,
        "terminal_policy": dict(_TERMINAL_PREAUTHORIZATION_POLICY),
    }


def verify_phase41_preauthorization(output_root: Path) -> PreparedPhase41Evaluation:
    """Verify preauthorization artifacts without accepting or touching a split path."""

    from src.model_adaptation.phase41_protocols import load_protocol_authority

    root = Path(output_root)
    request, request_bytes = _load_canonical_json(
        root / PREPARED_NAME, "Phase 41 evaluation request"
    )
    _validate_prepared(request)
    _require_canonical_production_authorities(request)
    protocols = load_protocol_authority(root)
    protocol_bytes = (root / PROTOCOLS_NAME).read_bytes()
    source, source_bytes = _load_canonical_json(
        root / SOURCE_MANIFEST_NAME, "Phase 41 execution source manifest"
    )
    materialization = _load_materialization_receipt(root)
    materialization_record = materialization[0] if materialization is not None else None
    repository_root = _materialized_source_root(root, materialization_record)
    if set(source) != {
        "schema_version",
        "preparation_scope",
        "upstream_declared_source_tree_sha256",
        "source_tree_sha256",
        "files",
        "launcher",
        "launcher_host",
        "python",
        "closed_import_roots",
        "alternate_evaluators_permitted",
    } or source["schema_version"] != "phase41-execution-source-manifest-v1":
        raise ContractError("execution source manifest fields drifted")
    if source["preparation_scope"] != request["preparation_scope"]:
        raise ContractError("execution source/request preparation scope drifted")
    if (
        source["preparation_scope"] == PRODUCTION_PREPARATION_SCOPE
        and source["upstream_declared_source_tree_sha256"]
        != request["authorities"].get("comparison_finalizer_source_sha256")
    ):
        raise ContractError("execution source differs from the Phase 40 source authority")
    _require_sha256(
        source["upstream_declared_source_tree_sha256"], "upstream execution source tree"
    )
    _require_sha256(source["source_tree_sha256"], "execution source tree")
    if source["alternate_evaluators_permitted"] is not False:
        raise ContractError("execution source permits an alternate evaluator")
    if source["closed_import_roots"] != list(_PHASE41_ENTRY_MODULES):
        raise ContractError("execution source entry-module roots drifted")
    python_authority = source["python"]
    if not isinstance(python_authority, dict) or set(python_authority) != {
        "path",
        "bytes",
        "sha256",
        "version",
        "runtime_import_roots",
    }:
        raise ContractError("execution Python authority drifted")
    python_path = Path(str(python_authority["path"]))
    import_roots = python_authority["runtime_import_roots"]
    if (
        not python_path.is_absolute()
        or not python_path.is_file()
        or python_path.is_symlink()
        or not isinstance(python_authority["bytes"], int)
        or isinstance(python_authority["bytes"], bool)
        or python_authority["bytes"] <= 0
        or not isinstance(python_authority["version"], str)
        or not re.fullmatch(r"\d+\.\d+\.\d+", python_authority["version"])
        or not isinstance(import_roots, list)
        or not import_roots
        or len(import_roots) != len(set(import_roots))
        or any(
            not isinstance(item, str)
            or not Path(item).is_absolute()
            or not Path(item).is_dir()
            or Path(item).is_symlink()
            for item in import_roots
        )
    ):
        raise ContractError("execution Python authority is unsafe")
    python_bytes = python_path.read_bytes()
    if (
        python_authority["bytes"] != len(python_bytes)
        or python_authority["sha256"] != _sha256(python_bytes)
    ):
        raise ContractError("execution Python bytes drifted")
    files = source["files"]
    if not isinstance(files, list) or not files:
        raise ContractError("execution source inventory is empty")
    expected_relative_files = _phase41_source_import_closure(repository_root)
    if tuple(
        item.get("path") if isinstance(item, dict) else None for item in files
    ) != expected_relative_files:
        raise ContractError("execution source inventory is not the exact import closure")
    verified_inventory: list[dict[str, object]] = []
    for item in files:
        if not isinstance(item, dict) or set(item) != {"path", "bytes", "sha256"}:
            raise ContractError("execution source inventory row drifted")
        relative = item["path"]
        if not isinstance(relative, str) or relative.startswith(("/", "\\")) or ".." in Path(relative).parts:
            raise ContractError("execution source inventory path escaped")
        candidate = repository_root / relative
        if not candidate.is_file() or candidate.is_symlink():
            raise ContractError("execution source inventory target is missing or unsafe")
        content = candidate.read_bytes()
        expected_item = {
            "path": relative,
            "bytes": len(content),
            "sha256": _sha256(content),
        }
        if item != expected_item:
            raise ContractError("execution source inventory content drifted")
        verified_inventory.append(expected_item)
    expected_tree = _sha256(
        b"phase41-execution-source-tree-v1\0"
        + _canonical_json_bytes(verified_inventory)
    )
    if source["source_tree_sha256"] != expected_tree:
        raise ContractError("execution source tree hash drifted")
    launcher = source["launcher"]
    if not isinstance(launcher, dict) or set(launcher) != {"path", "bytes", "sha256"}:
        raise ContractError("execution launcher authority drifted")
    if launcher["path"] != "scripts/phase41_one_shot_launcher.ps1":
        raise ContractError("execution launcher path drifted")
    if materialization is None:
        launcher_path = repository_root / launcher["path"]
        if not launcher_path.is_file() or launcher_path.is_symlink():
            raise ContractError("execution launcher is missing or unsafe")
        launcher_bytes = launcher_path.read_bytes()
        if launcher != {
            "path": "scripts/phase41_one_shot_launcher.ps1",
            "bytes": len(launcher_bytes),
            "sha256": _sha256(launcher_bytes),
        }:
            raise ContractError("execution launcher bytes drifted")
    launcher_host = source["launcher_host"]
    expected_launcher_host_fields = {"mode", "path", "bytes", "sha256"}
    if source["preparation_scope"] == PRODUCTION_PREPARATION_SCOPE:
        expected_launcher_host_fields.add("external_launch_receipt_sha256")
    if (
        not isinstance(launcher_host, dict)
        or set(launcher_host) != expected_launcher_host_fields
        or launcher_host["mode"]
        != (
            SYNTHETIC_PREPARATION_SCOPE
            if source["preparation_scope"] == SYNTHETIC_PREPARATION_SCOPE
            else "phase40_external_launcher_authority"
        )
        or not isinstance(launcher_host["path"], str)
        or not Path(launcher_host["path"]).is_absolute()
        or not isinstance(launcher_host["bytes"], int)
        or isinstance(launcher_host["bytes"], bool)
        or launcher_host["bytes"] <= 0
    ):
        raise ContractError("execution launcher host authority drifted")
    _require_sha256(launcher_host["sha256"], "execution launcher host")
    if source["preparation_scope"] == PRODUCTION_PREPARATION_SCOPE:
        if launcher_host["external_launch_receipt_sha256"] != request["authorities"].get(
            "comparison_launch_receipt_sha256"
        ):
            raise ContractError("external launcher authority differs from request")
        _require_sha256(
            launcher_host["external_launch_receipt_sha256"],
            "external Phase 40 launcher authority",
        )
    launcher_host_path = Path(launcher_host["path"])
    launcher_host_bytes = (
        launcher_host_path.read_bytes()
        if launcher_host_path.is_file() and not launcher_host_path.is_symlink()
        else b""
    )
    if (
        not launcher_host_path.is_file()
        or launcher_host_path.is_symlink()
        or len(launcher_host_bytes) != launcher_host["bytes"]
        or _sha256(launcher_host_bytes) != launcher_host["sha256"]
    ):
        raise ContractError("execution launcher host bytes drifted")
    if materialization is not None:
        _verify_materialization_receipt(
            receipt=materialization[0],
            receipt_bytes=materialization[1],
            source_root=repository_root,
            source=source,
            source_bytes=source_bytes,
            protocols_sha256=_sha256(protocol_bytes),
            model_bundle_authorities_sha256=_sha256(
                _canonical_json_bytes(request["authorities"]["model_bundle_authorities"])
            ),
            phase40_authority_hashes=request["authorities"],
        )
    authorities = request["authorities"]
    assert isinstance(authorities, dict)
    if authorities["protocols_sha256"] != _sha256(protocol_bytes):
        raise ContractError("protocol artifact hash differs from request")
    if authorities["execution_source_manifest_sha256"] != _sha256(source_bytes):
        raise ContractError("execution source manifest hash differs from request")
    models = _parse_models(request["models"])
    if (
        protocols.qwen.body["adapter_checkpoint_identity"]
        != models[0].selected_checkpoint_identity
        or protocols.phobert.body["classifier_checkpoint_identity"]
        != models[1].selected_checkpoint_identity
    ):
        raise ContractError("protocol/model checkpoint binding drifted")
    receipt, _ = _load_canonical_json(
        root / PREAUTHORIZATION_NAME, "Phase 41 preauthorization receipt"
    )
    if request["preparation_scope"] == PRODUCTION_PREPARATION_SCOPE:
        raw_smokes = receipt.get("model_smokes")
        if not isinstance(raw_smokes, list) or len(raw_smokes) != 2:
            raise ContractError("production preauthorization model smokes are incomplete")
        model_smokes: list[dict[str, object]] = []
        for protocol, item in zip(
            (protocols.qwen, protocols.phobert), raw_smokes, strict=True
        ):
            if (
                not isinstance(item, dict)
                or set(item)
                != {
                    "role",
                    "input_sha256",
                    "expected_state",
                    "observed_state",
                    "passed",
                }
                or item["role"] != protocol.role
                or item["input_sha256"]
                != protocol.body["synthetic_smoke"]["input_sha256"]
                or item["expected_state"]
                != protocol.body["synthetic_smoke"]["expected_state"]
                or item["observed_state"] != item["expected_state"]
                or item["passed"] is not True
            ):
                raise ContractError("production preauthorization model smoke drifted")
            model_smokes.append(dict(item))
        registry = _claim_registry_authority(_claim_registry_root())
        if receipt.get("claim_registry") != registry:
            raise ContractError("production preauthorization registry snapshot drifted")
        if (
            authorities["model_smokes_sha256"]
            != _sha256(_canonical_json_bytes(model_smokes))
            or authorities["claim_registry_authority_sha256"]
            != registry["authority_sha256"]
        ):
            raise ContractError("production smoke/registry authority hash drifted")
        expected_receipt = _production_preauthorization_record(
            request=request,
            request_bytes=request_bytes,
            authorities=authorities,
            model_smokes=model_smokes,
            claim_registry=registry,
        )
    else:
        expected_receipt = {
            "schema_version": "phase41-preauthorization-receipt-v1",
            "state": "prepared",
            "prepared_sha256": _sha256(request_bytes),
            "protocols_sha256": authorities["protocols_sha256"],
            "model_bundle_authorities_sha256": _sha256(
                _canonical_json_bytes(authorities["model_bundle_authorities"])
            ),
            "execution_source_manifest_sha256": authorities[
                "execution_source_manifest_sha256"
            ],
            "comparison_authority_sha256": authorities["comparison_authority_sha256"],
            "review_closure_sha256": authorities["review_closure_sha256"],
            "comparison_launch_receipt_sha256": authorities[
                "comparison_launch_receipt_sha256"
            ],
            **{
                name: authorities[name]
                for name in _PHASE40_REQUIRED_AUTHORITY_HASH_FIELDS
            },
            "models_ready_before_claim_required": True,
            "validation_contingency_closed_required": True,
        }
    if receipt != expected_receipt:
        raise ContractError("preauthorization receipt drifted")
    expected_bundle_authorities = [
        {
            "role": protocol.role,
            "bundle_root": protocol.body["bundle_root"],
            "bundle_root_sha256": protocol.body["bundle_root_sha256"],
        }
        for protocol in (protocols.qwen, protocols.phobert)
    ]
    if authorities["model_bundle_authorities"] != expected_bundle_authorities:
        raise ContractError("protocol/model bundle authority binding drifted")
    return PreparedPhase41Evaluation(root / PREPARED_NAME, _sha256(request_bytes))


def authorize_phase41_evaluation(
    output_root: Path,
    *,
    prepared_sha256: str,
    statement: str,
    deployment_fit_choice: str | None = None,
) -> Path:
    verified = verify_phase41_preauthorization(output_root)
    if prepared_sha256 != verified.prepared_sha256:
        raise AuthorizationError("authorization does not name the prepared request")
    return authorize_evaluation(
        output_root,
        operator_id="local-operator",
        statement=statement,
        deployment_fit_choice=deployment_fit_choice,
    )


def _validate_reserved_path_after_claim(path: Path) -> str:
    """Reject aliases and redirecting components after the claim is durable."""

    canonical = _normalize_reserved_path_without_io(path)

    candidate = Path(canonical)
    chain = list(reversed(candidate.parents)) + [candidate]
    for component in chain:
        attributes = _windows_file_attributes(component)
        if attributes & 0x400:
            raise ContractError("unsafe reserved path: reparse component detected")
    leaf_attributes = _windows_file_attributes(candidate)
    if leaf_attributes & 0x10:
        raise ContractError("unsafe reserved path: leaf is a directory")
    return canonical


def _strip_win32_final_prefix(value: str) -> str:
    if value.startswith("\\\\?\\UNC\\"):
        return "\\\\" + value[8:]
    if value.startswith("\\\\?\\"):
        return value[4:]
    return value


def _owned_split_opener(path: Path) -> BinaryIO:
    """Acquire the reserved payload through exactly one exclusive Win32 handle."""

    canonical = _validate_reserved_path_after_claim(path)
    if os.name != "nt":
        raise ContractError("Phase 41 production evaluation requires Windows")
    import ctypes
    from ctypes import wintypes
    import msvcrt

    GENERIC_READ = 0x80000000
    OPEN_EXISTING = 3
    FILE_ATTRIBUTE_NORMAL = 0x80
    FILE_FLAG_SEQUENTIAL_SCAN = 0x08000000
    invalid_handle = ctypes.c_void_p(-1).value

    class BY_HANDLE_FILE_INFORMATION(ctypes.Structure):
        _fields_ = [
            ("dwFileAttributes", wintypes.DWORD),
            ("ftCreationTime", wintypes.FILETIME),
            ("ftLastAccessTime", wintypes.FILETIME),
            ("ftLastWriteTime", wintypes.FILETIME),
            ("dwVolumeSerialNumber", wintypes.DWORD),
            ("nFileSizeHigh", wintypes.DWORD),
            ("nFileSizeLow", wintypes.DWORD),
            ("nNumberOfLinks", wintypes.DWORD),
            ("nFileIndexHigh", wintypes.DWORD),
            ("nFileIndexLow", wintypes.DWORD),
        ]

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    create_file = kernel32.CreateFileW
    create_file.argtypes = [
        wintypes.LPCWSTR,
        wintypes.DWORD,
        wintypes.DWORD,
        ctypes.c_void_p,
        wintypes.DWORD,
        wintypes.DWORD,
        wintypes.HANDLE,
    ]
    create_file.restype = wintypes.HANDLE
    get_final_path = kernel32.GetFinalPathNameByHandleW
    get_final_path.argtypes = [
        wintypes.HANDLE,
        wintypes.LPWSTR,
        wintypes.DWORD,
        wintypes.DWORD,
    ]
    get_final_path.restype = wintypes.DWORD
    get_file_information = kernel32.GetFileInformationByHandle
    get_file_information.argtypes = [
        wintypes.HANDLE,
        ctypes.POINTER(BY_HANDLE_FILE_INFORMATION),
    ]
    get_file_information.restype = wintypes.BOOL
    handle = create_file(
        canonical,
        GENERIC_READ,
        0,
        None,
        OPEN_EXISTING,
        FILE_ATTRIBUTE_NORMAL | FILE_FLAG_SEQUENTIAL_SCAN,
        None,
    )
    if handle == invalid_handle:
        raise ContractError(
            f"unsafe reserved path: exclusive CreateFileW failed ({ctypes.get_last_error()})"
        )
    transferred = False
    try:
        size = get_final_path(handle, None, 0, 0)
        if not size:
            raise ContractError("unsafe reserved path: final handle path unavailable")
        buffer = ctypes.create_unicode_buffer(size + 1)
        written = get_final_path(handle, buffer, len(buffer), 0)
        if not written or written >= len(buffer):
            raise ContractError("unsafe reserved path: final handle path changed")
        final_path = _strip_win32_final_prefix(buffer.value)
        if ntpath.normcase(ntpath.normpath(final_path)) != ntpath.normcase(canonical):
            raise ContractError("unsafe reserved path: final handle path mismatch")
        information = BY_HANDLE_FILE_INFORMATION()
        if not get_file_information(handle, ctypes.byref(information)):
            raise ContractError("unsafe reserved path: file identity unavailable")
        if information.dwFileAttributes & 0x410:
            raise ContractError("unsafe reserved path: final handle is redirecting or a directory")
        file_identity = f"{information.nFileIndexHigh:08x}{information.nFileIndexLow:08x}"
        _ACCESS_METADATA.set(
            _AccessMetadata(
                requested_path_sha256=_sha256(os.fspath(path).encode("utf-8")),
                final_path_sha256=_sha256(final_path.encode("utf-8")),
                volume_serial_number=int(information.dwVolumeSerialNumber),
                file_identity=file_identity,
            )
        )
        descriptor = msvcrt.open_osfhandle(
            int(handle), os.O_RDONLY | getattr(os, "O_BINARY", 0)
        )
        transferred = True
        return os.fdopen(descriptor, "rb", closefd=True)
    finally:
        if not transferred:
            kernel32.CloseHandle(handle)


def _artifact_hashes(root: Path, names: Sequence[str]) -> tuple[tuple[str, str], ...]:
    if tuple(names) != EVIDENCE_ARTIFACT_NAMES:
        raise ContractError("evidence artifact inventory differs from the fixed allowlist")
    canonical_root = Path(os.path.abspath(os.path.normpath(os.fspath(root))))
    hashes: list[tuple[str, str]] = []
    for name in names:
        if Path(name).name != name or Path(name).is_absolute() or name in {".", ".."}:
            raise ContractError("evidence artifact name escaped the fixed output root")
        candidate = canonical_root / name
        if candidate.parent != canonical_root:
            raise ContractError("evidence artifact path escaped the fixed output root")
        if not candidate.is_file() or candidate.is_symlink():
            raise ContractError(f"evidence artifact is missing or unsafe: {name}")
        hashes.append((name, _sha256(candidate.read_bytes())))
    return tuple(hashes)


def _manifest_from_disk(root: Path) -> Phase41EvidenceManifest:
    raw, payload = _load_canonical_json(
        root / EVIDENCE_MANIFEST_NAME, "Phase 41 evidence manifest"
    )
    if set(raw) != {"schema_version", "status", "artifacts", "terminal_policy"}:
        raise ContractError("evidence manifest fields drifted")
    if (
        raw["schema_version"] != "phase41-evidence-manifest-v1"
        or raw["status"] != "completed"
        or raw["terminal_policy"]
        != {
            "rerun_permitted": False,
            "test_outcome_used_for_tuning": False,
            "unbiased_test_score_claim_after_deployment_fit": False,
        }
    ):
        raise ContractError("evidence manifest terminal policy drifted")
    artifacts = raw["artifacts"]
    if not isinstance(artifacts, list):
        raise ContractError("evidence manifest artifacts must be a list")
    parsed: list[tuple[str, str]] = []
    for item in artifacts:
        if not isinstance(item, dict) or set(item) != {"name", "sha256"}:
            raise ContractError("evidence manifest artifact row drifted")
        if not isinstance(item["name"], str):
            raise ContractError("evidence artifact name is invalid")
        parsed.append((item["name"], _require_sha256(item["sha256"], "evidence artifact")))
    if tuple(name for name, _ in parsed) != EVIDENCE_ARTIFACT_NAMES:
        raise ContractError("evidence manifest inventory differs from the fixed allowlist")
    return Phase41EvidenceManifest(
        root / EVIDENCE_MANIFEST_NAME,
        "completed",
        _sha256(payload),
        tuple(parsed),
    )


def _freeze_completion_evidence(
    root: Path,
    products: _CompletionProducts,
    *,
    clock: Clock = _utc_now,
    finalization_guard: Callable[[], None] | None = None,
) -> None:
    """Freeze every local artifact, protect its seal, then write terminal last."""

    access_metadata = _ACCESS_METADATA.get()
    if access_metadata is None:
        raise ContractError("successful evaluation lacks owned-handle identity evidence")
    claim_sha = _sha256(products.claim_bytes)
    access = _canonical_json_bytes(
        {
            "schema_version": "phase41-evaluation-access-v1",
            "claim_sha256": claim_sha,
            "requested_path_sha256": access_metadata.requested_path_sha256,
            "final_path_sha256": access_metadata.final_path_sha256,
            "volume_serial_number": access_metadata.volume_serial_number,
            "file_identity": access_metadata.file_identity,
            "handle_acquisitions": 1,
            "sequential_payload_reads": 1,
            "observed_bytes": products.identity.bytes,
            "observed_sha256": products.identity.sha256,
            "observed_records": products.identity.records,
            "observed_label_counts": dict(products.identity.label_counts),
            "raw_content_retained": False,
        }
    )
    _exclusive_write(root / ACCESS_RECEIPT_NAME, access)
    if products.result.get("status") != "completed":
        raise ContractError("run-once did not produce completed results")
    hashes = _artifact_hashes(root, EVIDENCE_ARTIFACT_NAMES)
    manifest_payload = _canonical_json_bytes(
        {
            "schema_version": "phase41-evidence-manifest-v1",
            "status": "completed",
            "artifacts": [
                {"name": name, "sha256": digest} for name, digest in hashes
            ],
            "terminal_policy": {
                "rerun_permitted": False,
                "test_outcome_used_for_tuning": False,
                "unbiased_test_score_claim_after_deployment_fit": False,
            },
        }
    )
    _exclusive_write(root / EVIDENCE_MANIFEST_NAME, manifest_payload)
    terminal = {
        "schema_version": "phase41-terminal-v1",
        "status": "completed",
        "completed_at_utc": clock(),
        "claim_sha256": claim_sha,
        "evidence_manifest_sha256": _sha256(manifest_payload),
        "access_receipt_sha256": _sha256(access),
        "results_sha256": _sha256(products.results_bytes),
        "report_sha256": _sha256(products.report_bytes),
        "qwen_predictions_sha256": _sha256(products.qwen_predictions_bytes),
        "phobert_predictions_sha256": _sha256(products.phobert_predictions_bytes),
        "rerun_permitted": False,
    }
    terminal_payload = _canonical_json_bytes(terminal)
    seal_payload = _canonical_json_bytes(
        {
            "schema_version": "phase41-protected-completion-seal-v1",
            "status": "completed",
            "sealed_at_utc": clock(),
            "claim_sha256": claim_sha,
            "reserved_split_sha256": products.identity.sha256,
            "evidence_manifest_sha256": _sha256(manifest_payload),
            "terminal_sha256": _sha256(terminal_payload),
            "artifacts": [
                {"name": name, "sha256": digest} for name, digest in hashes
            ],
            "operator_sid": _current_operator_sid(),
            "meaning": "protected seal prevents consistent post-run evidence resealing",
        }
    )
    pending_payload = _canonical_json_bytes(
        {
            "schema_version": "phase41-protected-completion-journal-v1",
            "status": "completion_pending",
            "created_at_utc": clock(),
            "claim_sha256": claim_sha,
            "reserved_split_sha256": products.identity.sha256,
            "evidence_manifest_sha256": _sha256(manifest_payload),
            "intended_terminal_sha256": _sha256(terminal_payload),
            "intended_completion_seal_sha256": _sha256(seal_payload),
            "operator_sid": _current_operator_sid(),
            "meaning": "pending is non-success until atomically replaced by completed",
        }
    )
    global_completion = _global_completion_path(products.identity)
    try:
        _exclusive_global_claim_write(global_completion, pending_payload)
    except FileExistsError as exc:
        raise ContractError("protected completion journal already exists") from exc
    # Local completed evidence is provisional while the protected journal is
    # pending. The machine-global transition below is the final authoritative
    # success step. Any local/global failure is converted to spent_failed by
    # the enclosing run handler, and verification rejects a pending journal.
    _exclusive_write(root / COMPLETION_SEAL_NAME, seal_payload)
    _exclusive_write(root / TERMINAL_NAME, terminal_payload)
    if finalization_guard is not None:
        finalization_guard()
    _replace_global_completion(
        global_completion,
        pending_payload=pending_payload,
        completed_payload=seal_payload,
    )


def _validate_predictor_entry_mode(qwen, phobert) -> None:  # noqa: ANN001
    synthetic_runtime = _TEST_RUNTIME.get() is not None
    if synthetic_runtime:
        if (
            not qwen.synthetic_test_only
            or not phobert.synthetic_test_only
            or qwen.production_verified
            or phobert.production_verified
        ):
            raise ContractError(
                "synthetic runtime requires explicit synthetic-only predictor doubles"
            )
        return
    if (
        qwen.synthetic_test_only
        or phobert.synthetic_test_only
        or not qwen.production_verified
        or not phobert.production_verified
    ):
        raise ContractError(
            "production run requires loader-created and smoke-verified predictors"
        )


def _run_phase41_synthetic_with_predictors(
    output_root: Path, qwen, phobert  # noqa: ANN001
) -> Phase41EvidenceManifest:
    """Private callback tracer for durable synthetic-test requests only."""

    from src.model_adaptation.phase41_protocols import (
        FrozenPhoBertPredictor,
        FrozenQwenPredictor,
        load_protocol_authority,
    )

    if _TEST_RUNTIME.get() is None:
        raise ContractError("synthetic callback execution is unavailable in production")
    root = Path(output_root)
    _ensure_synthetic_materialization_receipt(root)
    materialization = _load_materialization_receipt(root)
    verify_phase41_preauthorization(root)
    if (
        type(qwen) is not FrozenQwenPredictor
        or type(phobert) is not FrozenPhoBertPredictor
    ):
        raise ContractError("run-once requires preloaded frozen Qwen and PhoBERT predictors")
    _validate_predictor_entry_mode(qwen, phobert)
    protocols = load_protocol_authority(root)
    if (
        qwen.protocol.protocol_sha256 != protocols.qwen.protocol_sha256
        or phobert.protocol.protocol_sha256 != protocols.phobert.protocol_sha256
    ):
        raise ContractError("predictor protocol identity drifted")
    _ACCESS_METADATA.set(None)
    _run_once(
        root,
        opener=_owned_split_opener,
        qwen_predictor=qwen,
        phobert_predictor=phobert,
        completion_writer=lambda products: _freeze_completion_evidence(root, products),
        preclaim_guard=lambda: None,
    )
    return _manifest_from_disk(root)


def _run_phase41_once_synthetic_for_test(
    output_root: Path, qwen, phobert  # noqa: ANN001
) -> Phase41EvidenceManifest:
    """Private synthetic tracer seam; unavailable outside the test runtime."""

    if _TEST_RUNTIME.get() is None:
        raise ContractError("synthetic run helper is unavailable in production")
    return _run_phase41_synthetic_with_predictors(output_root, qwen, phobert)


def _code_is_compiled_from_source(loader: object, source: bytes) -> bool:
    code = getattr(loader, "__code__", None)
    if not isinstance(code, CodeType):
        return False
    try:
        module_code = compile(
            source,
            code.co_filename,
            "exec",
            dont_inherit=True,
            optimize=0,
        )
    except (SyntaxError, ValueError):
        return False
    pending = [module_code]
    expected = marshal.dumps(code)
    while pending:
        candidate = pending.pop()
        if marshal.dumps(candidate) == expected:
            return True
        pending.extend(
            item for item in candidate.co_consts if isinstance(item, CodeType)
        )
    return False


def _verify_captured_production_loader(
    output_root: Path,
    protocol_module: ModuleType,
    captured_loader: object,
    reviewed_functions: tuple[tuple[str, object, CodeType], ...] = (),
) -> None:
    """Bind reviewed protocol callables to exact materialized source bytes."""

    root = Path(output_root)
    materialization = _load_materialization_receipt(root)
    if materialization is None:
        raise ContractError("the protected launcher materialization receipt is required")
    source, _ = _load_canonical_json(
        root / SOURCE_MANIFEST_NAME, "Phase 41 execution source manifest"
    )
    source_root = _materialized_source_root(root, materialization[0])
    relative = "src/model_adaptation/phase41_protocols.py"
    rows = source.get("files")
    matches = [
        row
        for row in rows
        if isinstance(rows, list)
        and isinstance(row, dict)
        and row.get("path") == relative
    ] if isinstance(rows, list) else []
    if len(matches) != 1:
        raise ContractError("production loader source authority is absent")
    authority = matches[0]
    expected_path = source_root / relative
    module_path_raw = getattr(protocol_module, "__file__", None)
    if not isinstance(module_path_raw, str):
        raise ContractError("production loader module has no bound source path")
    module_path = Path(module_path_raw)
    if (
        os.path.normcase(os.path.abspath(os.fspath(module_path)))
        != os.path.normcase(os.path.abspath(os.fspath(expected_path)))
        or not module_path.is_file()
        or module_path.is_symlink()
    ):
        raise ContractError("production loader module escaped its source authority")
    source_bytes = module_path.read_bytes()
    if authority.get("bytes") != len(source_bytes) or authority.get(
        "sha256"
    ) != _sha256(source_bytes):
        raise ContractError("production loader source/function identity drifted")
    callables = (("production predictor loader", captured_loader),) + tuple(
        (name, function) for name, function, _code in reviewed_functions
    )
    for name, function in callables:
        if (
            getattr(function, "__module__", None) != protocol_module.__name__
            or not _code_is_compiled_from_source(function, source_bytes)
        ):
            raise ContractError(f"{name} source/function identity drifted")
    for name, function, code in reviewed_functions:
        if getattr(function, "__code__", None) is not code:
            raise ContractError(f"{name} code identity drifted")


def _install_production_run_entry():  # noqa: ANN201
    """Capture reviewed protocol code before any live capability can exist."""

    import src.model_adaptation.phase41_protocols as protocol_module

    captured_loader = protocol_module.load_phase41_production_predictors
    captured_authority_loader = protocol_module.load_protocol_authority
    captured_state_helper = protocol_module._assert_loaded_predictor_state
    captured_qwen_type = protocol_module.FrozenQwenPredictor
    captured_phobert_type = protocol_module.FrozenPhoBertPredictor

    slot_names = (
        "protocol",
        "predictor",
        "loaded",
        "smoke_verified",
        "_leases",
        "_authority_sha256",
        "_output_root",
        "_launcher_binding",
        "_launcher_capability_sha256",
    )
    property_names = (
        "synthetic_test_only",
        "production_verified",
        "launcher_capability_sha256",
    )
    method_names = (
        "_has_launcher_binding",
        "assert_lifetime_integrity",
        "__call__",
    )

    def capture_predictor_contract(predictor_type):  # noqa: ANN001, ANN202
        namespace = vars(predictor_type)
        slots = tuple((name, namespace[name]) for name in slot_names)
        properties = []
        for name in property_names:
            descriptor = namespace[name]
            if not isinstance(descriptor, property) or descriptor.fget is None:
                raise RuntimeError(f"reviewed predictor property is invalid: {name}")
            code = getattr(descriptor.fget, "__code__", None)
            if not isinstance(code, CodeType):
                raise RuntimeError(f"reviewed predictor property has no code: {name}")
            properties.append((name, descriptor, descriptor.fget, code))
        methods = []
        for name in method_names:
            function = namespace[name]
            code = getattr(function, "__code__", None)
            if not isinstance(code, CodeType):
                raise RuntimeError(f"reviewed predictor method has no code: {name}")
            methods.append((name, function, code))
        return (predictor_type, slots, tuple(properties), tuple(methods))

    qwen_contract = capture_predictor_contract(captured_qwen_type)
    phobert_contract = capture_predictor_contract(captured_phobert_type)
    helper_code = getattr(captured_state_helper, "__code__", None)
    authority_loader_code = getattr(captured_authority_loader, "__code__", None)
    if not isinstance(helper_code, CodeType) or not isinstance(
        authority_loader_code, CodeType
    ):
        raise RuntimeError("reviewed protocol helpers have no code authority")

    reviewed_functions = (
        (
            "production predictor state helper",
            captured_state_helper,
            helper_code,
        ),
        (
            "protocol authority loader",
            captured_authority_loader,
            authority_loader_code,
        ),
    ) + tuple(
        (
            f"{contract[0].__name__}.{name}",
            function,
            code,
        )
        for contract in (qwen_contract, phobert_contract)
        for name, _descriptor, function, code in contract[2]
    ) + tuple(
        (
            f"{contract[0].__name__}.{name}",
            function,
            code,
        )
        for contract in (qwen_contract, phobert_contract)
        for name, function, code in contract[3]
    )

    def assert_reviewed_predictor_contract() -> None:
        """Reject in-place mutation of any reviewed production descriptor."""

        if protocol_module.load_phase41_production_predictors is not captured_loader:
            raise ContractError(
                "production loader binding drifted before capability acquisition"
            )
        if (
            protocol_module.load_protocol_authority is not captured_authority_loader
            or protocol_module._assert_loaded_predictor_state is not captured_state_helper
            or protocol_module.FrozenQwenPredictor is not captured_qwen_type
            or protocol_module.FrozenPhoBertPredictor is not captured_phobert_type
        ):
            raise ContractError("production predictor module binding drifted")
        for contract in (qwen_contract, phobert_contract):
            predictor_type, slots, properties, methods = contract
            namespace = vars(predictor_type)
            for name, descriptor in slots:
                if namespace.get(name) is not descriptor:
                    raise ContractError(
                        f"production predictor class descriptor drifted: {name}"
                    )
            for name, descriptor, function, code in properties:
                if (
                    namespace.get(name) is not descriptor
                    or descriptor.fget is not function
                    or function.__code__ is not code
                ):
                    raise ContractError(
                        f"production predictor class descriptor drifted: {name}"
                    )
            for name, function, code in methods:
                if namespace.get(name) is not function or function.__code__ is not code:
                    raise ContractError(
                        f"production predictor class descriptor drifted: {name}"
                    )
        for name, function, code in reviewed_functions[:2]:
            if function.__code__ is not code:
                raise ContractError(f"{name} code identity drifted")

    def contract_property(contract, name: str, predictor):  # noqa: ANN001, ANN202
        for candidate, _descriptor, function, _code in contract[2]:
            if candidate == name:
                return function(predictor)
        raise RuntimeError(f"uncaptured predictor property: {name}")

    def contract_slot(contract, name: str, predictor):  # noqa: ANN001, ANN202
        for candidate, descriptor in contract[1]:
            if candidate == name:
                return descriptor.__get__(predictor, contract[0])
        raise RuntimeError(f"uncaptured predictor slot: {name}")

    def call_contract_method(  # noqa: ANN202
        contract, name: str, predictor, *args  # noqa: ANN001
    ):
        for candidate, function, _code in contract[3]:
            if candidate == name:
                return function(predictor, *args)
        raise RuntimeError(f"uncaptured predictor method: {name}")

    def run_phase41_once(output_root: Path) -> Phase41EvidenceManifest:
        """Own production loader, predictors, handle, and irreversible run."""

        if _TEST_RUNTIME.get() is not None:
            raise ContractError("production run entry is unavailable in synthetic runtime")
        assert_reviewed_predictor_contract()
        root = Path(output_root)
        prepared_before_capability, _ = _load_canonical_json(
            root / PREPARED_NAME, "Phase 41 evaluation request"
        )
        _validate_prepared(prepared_before_capability)
        _require_canonical_production_authorities(prepared_before_capability)
        _verify_captured_production_loader(
            root,
            protocol_module,
            captured_loader,
            reviewed_functions,
        )
        assert_reviewed_predictor_contract()
        capability = _acquire_live_launcher_capability(root)
        token = _LIVE_LAUNCHER_CAPABILITY.set(capability)
        try:
            qwen, phobert = captured_loader(root)
            assert_reviewed_predictor_contract()
            if type(qwen) is not captured_qwen_type or type(phobert) is not captured_phobert_type:
                raise ContractError("production loader returned unexpected predictor types")
            verify_phase41_preauthorization(root)
            if (
                contract_property(qwen_contract, "synthetic_test_only", qwen)
                or contract_property(phobert_contract, "synthetic_test_only", phobert)
                or not contract_property(qwen_contract, "production_verified", qwen)
                or not contract_property(
                    phobert_contract, "production_verified", phobert
                )
            ):
                raise ContractError(
                    "production run requires loader-created and smoke-verified predictors"
                )
            protocols = captured_authority_loader(root)
            qwen_protocol = contract_slot(qwen_contract, "protocol", qwen)
            phobert_protocol = contract_slot(phobert_contract, "protocol", phobert)
            if (
                qwen_protocol.protocol_sha256 != protocols.qwen.protocol_sha256
                or phobert_protocol.protocol_sha256
                != protocols.phobert.protocol_sha256
            ):
                raise ContractError("predictor protocol identity drifted")
            materialization = _load_materialization_receipt(root)
            if materialization is None:
                raise ContractError("the protected launcher materialization receipt is required")
            live_binding = _require_live_launcher_capability(root, consume=False)
            expected_capability_sha = materialization[0]["launcher_capability_sha256"]
            for contract, predictor in (
                (qwen_contract, qwen),
                (phobert_contract, phobert),
            ):
                if (
                    not call_contract_method(
                        contract,
                        "_has_launcher_binding",
                        predictor,
                        live_binding,
                    )
                    or contract_property(
                        contract,
                        "launcher_capability_sha256",
                        predictor,
                    )
                    != expected_capability_sha
                ):
                    raise ContractError(
                        "production predictor lacks the live loader/lease binding"
                    )

            def assert_predictor_lifetimes() -> None:
                assert_reviewed_predictor_contract()
                for contract, predictor in (
                    (qwen_contract, qwen),
                    (phobert_contract, phobert),
                ):
                    call_contract_method(
                        contract,
                        "assert_lifetime_integrity",
                        predictor,
                    )
                if (
                    _require_live_launcher_capability(root, consume=False)
                    is not live_binding
                ):
                    raise ContractError("live launcher capability binding changed")

            prepared, prepared_bytes = _load_canonical_json(
                root / PREPARED_NAME, "Phase 41 evaluation request"
            )
            identity, models = _validate_prepared(prepared)
            _require_canonical_production_authorities(prepared)
            authorization, authorization_bytes = _load_canonical_json(
                root / AUTHORIZATION_NAME, "Phase 41 explicit authorization"
            )
            prepared_sha = _sha256(prepared_bytes)
            authorization_sha = _sha256(authorization_bytes)
            prepared_precommit = prepared["deployment_fit_precommit"]
            assert isinstance(prepared_precommit, dict)
            precommit = _validate_authorization(
                authorization,
                prepared_sha256=prepared_sha,
                phase40_authorities_sha256=_phase40_authorities_sha256(prepared),
                prepared_deployment_fit_precommit=prepared_precommit,
            )
            if identity.path != _normalize_reserved_path_without_io(identity.path):
                raise ContractError("reserved path lexical authority drifted before claim")
            precommit_sha = _sha256(_canonical_json_bytes(precommit))
            global_claim = _global_claim_path(identity)
            _assert_unspent_and_clean(root, global_claim)
            assert_predictor_lifetimes()
            if _require_live_launcher_capability(root, consume=True) is not live_binding:
                raise ContractError("live launcher capability changed before claim")
            _, claim_bytes = _claim_once(
                root,
                identity=identity,
                prepared_sha256=prepared_sha,
                authorization_sha256=authorization_sha,
                materialization_receipt_sha256=_sha256(materialization[1]),
                deployment_fit_precommit_sha256=precommit_sha,
                claimed_at_utc=_utc_now(),
                clock=_utc_now,
            )
            claim_sha = _sha256(claim_bytes)
            stage = "open_reserved_split"
            try:
                if (root / PREPARED_NAME).read_bytes() != prepared_bytes:
                    raise ContractError("prepared request changed after the durable claim")
                if (root / AUTHORIZATION_NAME).read_bytes() != authorization_bytes:
                    raise ContractError("authorization changed after the durable claim")
                _ACCESS_METADATA.set(None)
                loaded = _open_snapshot_once(identity, _owned_split_opener)

                stage = "qwen_prediction"
                assert_predictor_lifetimes()
                qwen_predictions = _validated_predictions(
                    call_contract_method(
                        qwen_contract,
                        "__call__",
                        qwen,
                        loaded.predictor_view,
                    ),
                    loaded.predictor_view,
                    role="qwen",
                )
                assert_predictor_lifetimes()
                stage = "phobert_prediction"
                phobert_predictions = _validated_predictions(
                    call_contract_method(
                        phobert_contract,
                        "__call__",
                        phobert,
                        loaded.predictor_view,
                    ),
                    loaded.predictor_view,
                    role="phobert",
                )
                assert_predictor_lifetimes()
                gold = tuple(row.gold_label for row in loaded.rows)
                qwen_metrics = compute_metrics(gold, qwen_predictions)
                phobert_metrics = compute_metrics(gold, phobert_predictions)
                statements = comparison_statements(qwen_metrics, phobert_metrics)

                stage = "freeze_outputs"
                qwen_bytes = _prediction_jsonl(
                    "qwen", models[0].run_id, loaded.rows, qwen_predictions
                )
                phobert_bytes = _prediction_jsonl(
                    "phobert", models[1].run_id, loaded.rows, phobert_predictions
                )
                _exclusive_write(root / QWEN_PREDICTIONS_NAME, qwen_bytes)
                _exclusive_write(root / PHOBERT_PREDICTIONS_NAME, phobert_bytes)
                result: dict[str, object] = {
                    "schema_version": "phase41-one-shot-results-v1",
                    "status": "completed",
                    "prepared_sha256": prepared_sha,
                    "authorization_sha256": authorization_sha,
                    "claim_sha256": claim_sha,
                    "held_out": {
                        "records": len(loaded.rows),
                        "bytes": loaded.payload_bytes,
                        "sha256": identity.sha256,
                    },
                    "prior_exposure": {
                        "human_content_exposure_disclosed": prepared["authorities"].get(
                            "prior_human_exposure_disclosed", False
                        ),
                        "claim": "one_post_freeze_model_evaluation_pass",
                    },
                    "models": [
                        {
                            "role": models[0].role,
                            "run_id": models[0].run_id,
                            "artifact_sha256": models[0].artifact_sha256,
                            "selected_checkpoint_identity": models[0].selected_checkpoint_identity,
                            "predictions_sha256": _sha256(qwen_bytes),
                            "metrics": qwen_metrics,
                        },
                        {
                            "role": models[1].role,
                            "run_id": models[1].run_id,
                            "artifact_sha256": models[1].artifact_sha256,
                            "selected_checkpoint_identity": models[1].selected_checkpoint_identity,
                            "predictions_sha256": _sha256(phobert_bytes),
                            "metrics": phobert_metrics,
                        },
                    ],
                    "comparison_statements": list(statements),
                    "terminal_policy": {
                        "rerun_permitted": False,
                        "test_driven_training_action_permitted": False,
                        "test_driven_checkpoint_selection_permitted": False,
                        "test_driven_dataset_repair_permitted": False,
                        "test_driven_contingency_activation_permitted": False,
                    },
                }
                result_bytes = _canonical_json_bytes(result)
                report_bytes = _render_report(result)
                _exclusive_write(root / RESULTS_NAME, result_bytes)
                _exclusive_write(root / REPORT_NAME, report_bytes)
                stage = "freeze_completion_evidence"
                _freeze_completion_evidence(
                    root,
                    _CompletionProducts(
                        result=result,
                        identity=identity,
                        prepared=prepared,
                        models=models,
                        claim_bytes=claim_bytes,
                        qwen_predictions_bytes=qwen_bytes,
                        phobert_predictions_bytes=phobert_bytes,
                        results_bytes=result_bytes,
                        report_bytes=report_bytes,
                    ),
                    finalization_guard=assert_predictor_lifetimes,
                )
            except BaseException as exc:
                _terminal_failure(root, claim_sha, stage, exc, _utc_now)
                raise
            return _manifest_from_disk(root)
        finally:
            _LIVE_LAUNCHER_CAPABILITY.reset(token)
            capability.close()

    return run_phase41_once


run_phase41_once = _install_production_run_entry()
del _install_production_run_entry


def _verify_protected_completion_seal(root: Path) -> None:
    request, request_bytes = _load_canonical_json(
        root / PREPARED_NAME, "Phase 41 request"
    )
    identity, _ = _validate_prepared(request)
    _require_canonical_production_authorities(request)
    authorization, _ = _load_canonical_json(
        root / AUTHORIZATION_NAME, "Phase 41 explicit authorization"
    )
    prepared_precommit = request["deployment_fit_precommit"]
    assert isinstance(prepared_precommit, dict)
    _validate_authorization(
        authorization,
        prepared_sha256=_sha256(request_bytes),
        phase40_authorities_sha256=_phase40_authorities_sha256(request),
        prepared_deployment_fit_precommit=prepared_precommit,
    )
    _validate_claim_registry_root(_claim_registry_root())
    claim, claim_bytes = _load_canonical_json(root / CLAIM_NAME, "Phase 41 claim")
    local, local_bytes = _load_canonical_json(
        root / COMPLETION_SEAL_NAME, "Phase 41 protected completion seal"
    )
    protected, protected_bytes = _load_canonical_json(
        _global_completion_path(identity),
        "Phase 41 machine-local protected completion seal",
    )
    if local != protected or local_bytes != protected_bytes:
        raise ContractError("local and protected completion seals differ")
    manifest = _manifest_from_disk(root)
    terminal, terminal_bytes = _load_canonical_json(
        root / TERMINAL_NAME, "Phase 41 terminal record"
    )
    expected_artifacts = [
        {"name": name, "sha256": digest} for name, digest in manifest.artifacts
    ]
    if set(local) != {
        "schema_version",
        "status",
        "sealed_at_utc",
        "claim_sha256",
        "reserved_split_sha256",
        "evidence_manifest_sha256",
        "terminal_sha256",
        "artifacts",
        "operator_sid",
        "meaning",
    } or (
        local["schema_version"] != "phase41-protected-completion-seal-v1"
        or local["status"] != "completed"
        or not isinstance(local["sealed_at_utc"], str)
        or not local["sealed_at_utc"]
        or local["claim_sha256"] != _sha256(claim_bytes)
        or local["reserved_split_sha256"] != identity.sha256
        or local["evidence_manifest_sha256"] != manifest.evidence_manifest_sha256
        or local["terminal_sha256"] != _sha256(terminal_bytes)
        or local["artifacts"] != expected_artifacts
        or local["operator_sid"] != claim.get("operator_sid")
        or local["meaning"]
        != "protected seal prevents consistent post-run evidence resealing"
        or terminal.get("evidence_manifest_sha256")
        != manifest.evidence_manifest_sha256
    ):
        raise ContractError("protected completion seal differs from terminal evidence")


def _verify_phase41_evidence_core(
    output_root: Path, *, require_disposition: bool
) -> Phase41EvidenceManifest:
    """Verify already-frozen evidence without any predictor, opener, or split argument."""

    root = Path(output_root)
    _verify_protected_completion_seal(root)
    verify_only(root)
    request, request_bytes = _load_canonical_json(
        root / PREPARED_NAME, "Phase 41 request"
    )
    identity, _ = _validate_prepared(request)
    _require_canonical_production_authorities(request)
    authorization, _ = _load_canonical_json(
        root / AUTHORIZATION_NAME, "Phase 41 explicit authorization"
    )
    prepared_precommit = request["deployment_fit_precommit"]
    assert isinstance(prepared_precommit, dict)
    effective_precommit = _validate_authorization(
        authorization,
        prepared_sha256=_sha256(request_bytes),
        phase40_authorities_sha256=_phase40_authorities_sha256(request),
        prepared_deployment_fit_precommit=prepared_precommit,
    )
    claim_bytes = (root / CLAIM_NAME).read_bytes()
    access, _ = _load_canonical_json(
        root / ACCESS_RECEIPT_NAME, "Phase 41 evaluation access receipt"
    )
    if set(access) != {
        "schema_version",
        "claim_sha256",
        "requested_path_sha256",
        "final_path_sha256",
        "volume_serial_number",
        "file_identity",
        "handle_acquisitions",
        "sequential_payload_reads",
        "observed_bytes",
        "observed_sha256",
        "observed_records",
        "observed_label_counts",
        "raw_content_retained",
    }:
        raise ContractError("evaluation access receipt fields drifted")
    if (
        access["schema_version"] != "phase41-evaluation-access-v1"
        or access["claim_sha256"] != _sha256(claim_bytes)
        or access["requested_path_sha256"]
        != _sha256(identity.path.encode("utf-8"))
        or not isinstance(access["final_path_sha256"], str)
        or not SHA256_RE.fullmatch(access["final_path_sha256"])
        or not isinstance(access["volume_serial_number"], int)
        or isinstance(access["volume_serial_number"], bool)
        or access["volume_serial_number"] < 0
        or not isinstance(access["file_identity"], str)
        or not re.fullmatch(r"[0-9a-f]{16}", access["file_identity"])
        or access["handle_acquisitions"] != 1
        or access["sequential_payload_reads"] != 1
        or access["observed_bytes"] != identity.bytes
        or access["observed_sha256"] != identity.sha256
        or access["observed_records"] != identity.records
        or access["observed_label_counts"] != dict(identity.label_counts)
        or access["raw_content_retained"] is not False
    ):
        raise ContractError("evaluation access receipt authority drifted")
    terminal, terminal_bytes = _load_canonical_json(
        root / TERMINAL_NAME, "Phase 41 terminal record"
    )
    if terminal.get("access_receipt_sha256") != _sha256(
        (root / ACCESS_RECEIPT_NAME).read_bytes()
    ):
        raise ContractError("terminal access-receipt hash drifted")
    manifest = _manifest_from_disk(root)
    expected = _artifact_hashes(root, EVIDENCE_ARTIFACT_NAMES)
    if expected != manifest.artifacts:
        raise ContractError("evidence manifest artifact hashes drifted")
    disposition_path = root / DEPLOYMENT_DISPOSITION_NAME
    if not disposition_path.is_file() or disposition_path.is_symlink():
        if require_disposition:
            raise ContractError("deployment-fit disposition is mandatory for final verification")
    else:
        disposition, _ = _load_canonical_json(
            disposition_path, "Phase 41 deployment-fit disposition"
        )
        if set(disposition) != {
            "schema_version",
            "choice",
            "evidence_manifest_sha256",
            "terminal_sha256",
            "protected_completion_seal_sha256",
            "deployment_fit_precommit_sha256",
            "selected_checkpoint_identities",
            "unbiased_test_score_claim",
            "test_outcome_used_for_tuning",
        }:
            raise ContractError("deployment-fit disposition fields drifted")
        if (
            disposition["schema_version"] != "phase41-deployment-fit-disposition-v1"
            or disposition["evidence_manifest_sha256"]
            != manifest.evidence_manifest_sha256
            or disposition["terminal_sha256"] != _sha256(terminal_bytes)
            or disposition["protected_completion_seal_sha256"]
            != _sha256((root / COMPLETION_SEAL_NAME).read_bytes())
            or disposition["unbiased_test_score_claim"] is not False
            or disposition["test_outcome_used_for_tuning"] is not False
        ):
            raise ContractError("deployment-fit disposition authority drifted")
        parsed_disposition = DeploymentFitDisposition(
            choice=disposition["choice"],  # type: ignore[arg-type]
            selected_checkpoint_identities=tuple(
                disposition["selected_checkpoint_identities"]  # type: ignore[arg-type]
            ),
        )
        expected_disposition = DeploymentFitDisposition(
            choice=str(effective_precommit["choice"]),
            selected_checkpoint_identities=tuple(
                effective_precommit["selected_checkpoint_identities"]  # type: ignore[arg-type]
            ),
        )
        if (
            parsed_disposition != expected_disposition
            or disposition["deployment_fit_precommit_sha256"]
            != _sha256(_canonical_json_bytes(effective_precommit))
        ):
            raise ContractError("deployment-fit disposition differs from precommitment")
    return manifest


def verify_phase41_evidence(output_root: Path) -> Phase41EvidenceManifest:
    """Verify a complete bundle, including its mandatory fixed disposition."""

    return _verify_phase41_evidence_core(output_root, require_disposition=True)


def freeze_deployment_fit_disposition(output_root: Path) -> Path:
    root = Path(output_root)
    manifest = _verify_phase41_evidence_core(root, require_disposition=False)
    request, request_bytes = _load_canonical_json(
        root / PREPARED_NAME, "Phase 41 request"
    )
    _validate_prepared(request)
    _require_canonical_production_authorities(request)
    authorization, _ = _load_canonical_json(
        root / AUTHORIZATION_NAME, "Phase 41 explicit authorization"
    )
    prepared_precommit = request["deployment_fit_precommit"]
    assert isinstance(prepared_precommit, dict)
    precommit = _validate_authorization(
        authorization,
        prepared_sha256=_sha256(request_bytes),
        phase40_authorities_sha256=_phase40_authorities_sha256(request),
        prepared_deployment_fit_precommit=prepared_precommit,
    )
    _, terminal_bytes = _load_canonical_json(
        root / TERMINAL_NAME, "Phase 41 terminal record"
    )
    _, completion_seal_bytes = _load_canonical_json(
        root / COMPLETION_SEAL_NAME, "Phase 41 protected completion seal"
    )
    payload = _canonical_json_bytes(
        {
            "schema_version": "phase41-deployment-fit-disposition-v1",
            "choice": precommit["choice"],
            "evidence_manifest_sha256": manifest.evidence_manifest_sha256,
            "terminal_sha256": _sha256(terminal_bytes),
            "protected_completion_seal_sha256": _sha256(completion_seal_bytes),
            "deployment_fit_precommit_sha256": _sha256(
                _canonical_json_bytes(precommit)
            ),
            "selected_checkpoint_identities": precommit[
                "selected_checkpoint_identities"
            ],
            "unbiased_test_score_claim": False,
            "test_outcome_used_for_tuning": False,
        }
    )
    return _exclusive_write(root / DEPLOYMENT_DISPOSITION_NAME, payload)


def selected_phase41_checkpoint_identities(output_root: Path) -> tuple[str, str]:
    verify_phase41_preauthorization(output_root)
    request, _ = _load_canonical_json(
        Path(output_root) / PREPARED_NAME, "Phase 41 request"
    )
    models = _parse_models(request["models"])
    return tuple(model.selected_checkpoint_identity for model in models)


def _code_fixed_authority_path(
    repo_root: Path, supplied: Path, expected_relative: Path, description: str
) -> Path:
    root = Path(os.path.abspath(os.path.normpath(os.fspath(repo_root))))
    expected = Path(os.path.abspath(os.path.normpath(os.fspath(root / expected_relative))))
    candidate = Path(supplied)
    if not candidate.is_absolute():
        candidate = root / candidate
    candidate = Path(os.path.abspath(os.path.normpath(os.fspath(candidate))))
    if os.path.normcase(os.fspath(candidate)) != os.path.normcase(os.fspath(expected)):
        raise ContractError(f"{description} path is not the code-fixed authority")
    return expected


def _phase39_opaque_authority(
    path: Path, *, repo_root: Path | None = None
) -> tuple[OpaqueHeldOutAuthority, str]:
    if not path.is_file() or path.is_symlink():
        raise ContractError("Phase 39 downstream authority is missing or unsafe")
    payload = path.read_bytes()
    raw = _parse_json_bytes(payload, "Phase 39 downstream authority")
    expected_fields = {
        "schema_version",
        "generated_at",
        "source_manifest",
        "total_records",
        "splits",
        "total_label_counts",
        "split_governance",
        "phase40_training_boundary",
        "held_out_test",
        "phase41_post_evaluation_fit",
    }
    if set(raw) != expected_fields or raw["schema_version"] != (
        "phase39-downstream-data-contract-v1"
    ):
        raise ContractError("Phase 39 downstream authority fields/schema drifted")
    splits = raw["splits"]
    held_out = raw["held_out_test"]
    boundary = raw["phase40_training_boundary"]
    post_fit = raw["phase41_post_evaluation_fit"]
    if (
        not isinstance(splits, dict)
        or set(splits) != {"train", "val", "test"}
        or not isinstance(held_out, dict)
        or set(held_out)
        != {"path", "records", "bytes", "sha256", "evaluation_phase", "touch_policy"}
        or not isinstance(boundary, dict)
        or boundary.get("allowed_splits") != ["train", "val"]
        or boundary.get("forbidden_split") != "test"
        or not isinstance(post_fit, dict)
        or post_fit.get("unbiased_test_score_claim") is not False
    ):
        raise ContractError("Phase 39 train/validation/held-out boundary drifted")
    test = splits["test"]
    if not isinstance(test, dict) or set(test) != {
        "records",
        "bytes",
        "sha256",
        "label_counts",
    }:
        raise ContractError("Phase 39 held-out split metadata fields drifted")
    counts = test["label_counts"]
    if not isinstance(counts, dict) or set(counts) != set(LABEL_ORDER):
        raise ContractError("Phase 39 held-out label support drifted")
    ordered_counts: list[tuple[str, int]] = []
    for label in LABEL_ORDER:
        count = counts[label]
        if not isinstance(count, int) or isinstance(count, bool) or count <= 0:
            raise ContractError("Phase 39 held-out labels require positive support")
        ordered_counts.append((label, count))
    records = test["records"]
    byte_count = test["bytes"]
    if (
        not isinstance(records, int)
        or isinstance(records, bool)
        or records <= 0
        or not isinstance(byte_count, int)
        or isinstance(byte_count, bool)
        or byte_count <= 0
        or sum(count for _, count in ordered_counts) != records
        or held_out.get("records") != records
        or held_out.get("bytes") != byte_count
        or held_out.get("sha256") != test["sha256"]
        or held_out.get("path") != "data/splits/test.jsonl"
        or held_out.get("evaluation_phase") != 41
        or not isinstance(held_out.get("touch_policy"), str)
        or not str(held_out["touch_policy"]).strip()
    ):
        raise ContractError("Phase 39 opaque held-out identity failed reconciliation")
    held_out_sha = _require_sha256(test["sha256"], "Phase 39 held-out")

    split_identities: dict[str, dict[str, object]] = {}
    total_records = 0
    aggregate_counts = {label: 0 for label in LABEL_ORDER}
    for split_name in ("train", "val"):
        split = splits[split_name]
        if not isinstance(split, dict) or set(split) != {
            "records",
            "bytes",
            "sha256",
            "label_counts",
        }:
            raise ContractError(f"Phase 39 {split_name} metadata fields drifted")
        split_counts = split["label_counts"]
        if not isinstance(split_counts, dict) or set(split_counts) != set(LABEL_ORDER):
            raise ContractError(f"Phase 39 {split_name} label support drifted")
        normalized_counts: list[tuple[str, int]] = []
        for label in LABEL_ORDER:
            count = split_counts[label]
            if not isinstance(count, int) or isinstance(count, bool) or count < 0:
                raise ContractError(f"Phase 39 {split_name} label support is invalid")
            aggregate_counts[label] += count
            normalized_counts.append((label, count))
        split_records = split["records"]
        split_bytes = split["bytes"]
        if (
            not isinstance(split_records, int)
            or isinstance(split_records, bool)
            or split_records <= 0
            or sum(count for _, count in normalized_counts) != split_records
            or not isinstance(split_bytes, int)
            or isinstance(split_bytes, bool)
            or split_bytes <= 0
        ):
            raise ContractError(f"Phase 39 {split_name} metadata is inconsistent")
        total_records += split_records
        split_identities[split_name] = {
            "split_name": split_name,
            "relative_path": f"data/splits/{split_name}.jsonl",
            "records": split_records,
            "bytes": split_bytes,
            "sha256": _require_sha256(split["sha256"], f"Phase 39 {split_name}"),
            "label_counts": normalized_counts,
        }
    total_records += records
    for label, count in ordered_counts:
        aggregate_counts[label] += count
    if raw["total_records"] != total_records or raw["total_label_counts"] != aggregate_counts:
        raise ContractError("Phase 39 aggregate record/label totals drifted")

    held_out_identity = {
        "path": held_out["path"],
        "records": records,
        "bytes": byte_count,
        "sha256": held_out_sha,
        "evaluation_phase": 41,
        "touch_policy": held_out["touch_policy"],
    }
    phase40_contract_identity = _sha256(
        _canonical_json_bytes(
            {
                "train": split_identities["train"],
                "val": split_identities["val"],
                "held_out_opaque": held_out_identity,
            }
        )
    )
    declared_path = str(held_out["path"])
    if repo_root is not None:
        # Pure lexical resolution only. Do not resolve(), stat(), hash(), or
        # open the held-out target during preparation.
        declared_path = os.path.abspath(
            os.path.normpath(os.fspath(Path(repo_root) / declared_path))
        )
        declared_path = _normalize_reserved_path_without_io(declared_path)
    return (
        OpaqueHeldOutAuthority(
            path=declared_path,
            records=records,
            bytes=byte_count,
            sha256=held_out_sha,
            label_counts=tuple(ordered_counts),
        ),
        phase40_contract_identity,
    )


def _enum_text(value: object) -> object:
    return getattr(value, "value", value)


def _verify_phase40_model_bundle(
    *, repo_root: Path, comparison_run, expected_role: str
) -> FrozenModelIdentity:
    from src.model_adaptation.phase40_evidence import verify_phase40_bundle

    expected_family, expected_adaptation, phase41_adaptation, checkpoint_prefix = {
        "qwen": ("qwen", "qlora", "qlora", "adapter-state-sha256:"),
        "phobert": (
            "phobert",
            "classification-head",
            "classification_head",
            "model-state-sha256:",
        ),
    }[expected_role]
    returned_root = str(comparison_run.returned_root)
    expected_root = _PHASE40_RETURNED_ROOTS[0 if expected_role == "qwen" else 1]
    if returned_root != expected_root:
        raise ContractError(f"Phase 40 {expected_role} returned root drifted")
    run_root = Path(repo_root) / returned_root
    try:
        evidence = verify_phase40_bundle(run_root)
    except Exception as exc:
        raise ContractError(f"Phase 40 {expected_role} bundle verification failed") from exc
    evidence_path = run_root / "run-evidence.json"
    if (
        not evidence_path.is_file()
        or evidence_path.is_symlink()
        or _sha256(evidence_path.read_bytes()) != comparison_run.evidence_sha256
    ):
        raise ContractError(f"Phase 40 {expected_role} evidence hash drifted")
    identity = evidence.experiment_identity
    selected = evidence.selected_checkpoint
    artifacts = tuple(
        artifact for artifact in evidence.artifacts if artifact.role == "model_artifact"
    )
    if (
        _enum_text(evidence.status) != "complete"
        or _enum_text(identity.run_kind) != "full"
        or _enum_text(identity.model_family) != expected_family
        or _enum_text(identity.adaptation_mode) != expected_adaptation
        or evidence.run_id != comparison_run.run_id
        or evidence.resume_digest != comparison_run.resume_digest
        or evidence.comparison_eligible is not True
        or selected is None
        or selected.artifact_identity != comparison_run.selected_checkpoint_identity
        or selected.optimizer_step != comparison_run.selected_optimizer_step
        or selected.safety_gate_passed is not True
        or comparison_run.comparison_eligible is not True
        or comparison_run.safety_gate_passed is not True
        or evidence.validation_metrics != comparison_run.validation_metrics
        or evidence.package_versions != comparison_run.package_versions
        or len(artifacts) != 1
    ):
        raise ContractError(f"Phase 40 {expected_role} comparison/bundle identity drifted")
    checkpoint = str(selected.artifact_identity)
    if not checkpoint.startswith(checkpoint_prefix):
        raise ContractError(f"Phase 40 {expected_role} selected checkpoint kind drifted")
    _require_sha256(
        checkpoint.removeprefix(checkpoint_prefix),
        f"Phase 40 {expected_role} selected checkpoint",
    )
    return FrozenModelIdentity(
        role=expected_role,
        run_id=str(evidence.run_id),
        model_family=expected_family,
        adaptation_mode=phase41_adaptation,
        artifact_sha256=str(artifacts[0].sha256),
        selected_checkpoint_identity=checkpoint,
    )


def _verify_phase40_closure(
    *,
    repo_root: Path,
    comparison_path: Path,
    review_path: Path,
    phase39_contract_identity: str,
) -> tuple[tuple[FrozenModelIdentity, FrozenModelIdentity], str, str]:
    from src.model_adaptation.phase40_handoff import (
        PHASE40_COMPARISON_SCHEMA_VERSION,
        PHASE40_COMPARISON_LIMITATIONS,
        Phase40ComparisonManifest,
    )
    from src.model_adaptation.phase40_production_authorities import (
        PORTABLE_RECEIPTS_ONLY,
        VerifiedPhase40ProductionAuthorities,
        load_phase40_portable_production_authorities,
    )

    comparison_raw, comparison_bytes = _load_canonical_json(
        comparison_path, "Phase 40 comparison manifest"
    )
    try:
        comparison = Phase40ComparisonManifest.model_validate(comparison_raw)
    except Exception as exc:
        raise ContractError("Phase 40 comparison manifest schema is invalid") from exc
    if comparison_bytes != _canonical_json_bytes(comparison.model_dump(mode="json")):
        raise ContractError("Phase 40 comparison manifest differs from its typed authority")
    if (
        comparison.status != "complete"
        or comparison.schema_version != PHASE40_COMPARISON_SCHEMA_VERSION
        or comparison.production_authority_verification_mode
        != "portable_receipts_only"
        or comparison.quality_comparison_admissible is not True
        or comparison.failure_reason is not None
        or comparison.speed_comparison_admissible is not False
        or comparison.execution_policy != "local_primary"
        or comparison.full_lora_disposition != "cancelled_before_start"
        or comparison.limitations != PHASE40_COMPARISON_LIMITATIONS
        or len(comparison.runs) != 2
        or tuple(
            (_enum_text(run.model_family), _enum_text(run.adaptation_mode))
            for run in comparison.runs
        )
        != (("qwen", "qlora"), ("phobert", "classification-head"))
        or not all(
            run.comparison_eligible and run.safety_gate_passed
            for run in comparison.runs
        )
    ):
        raise ContractError("Phase 40 comparison is not a closed admissible two-model result")
    try:
        production = load_phase40_portable_production_authorities(
            repo_root=repo_root
        )
    except Exception as exc:
        raise ContractError(
            "Phase 40 fixed portable production authority closure is invalid"
        ) from exc
    if type(production) is not VerifiedPhase40ProductionAuthorities:
        raise ContractError(
            "Phase 40 fixed authority loader returned an untrusted closure type"
        )
    production_values = production.as_dict()
    if production_values.get("verification_mode") != PORTABLE_RECEIPTS_ONLY:
        raise ContractError(
            "Phase 40 authority closure must remain portable-receipts-only"
        )
    comparison_authority_fields = (
        "comparison_launch_receipt_sha256",
        *_PHASE40_REQUIRED_AUTHORITY_HASH_FIELDS,
    )
    if any(
        getattr(comparison, name) != production_values.get(name)
        for name in comparison_authority_fields
    ):
        raise ContractError(
            "Phase 40 comparison portable receipt closure differs from fixed authorities"
        )
    models = tuple(
        _verify_phase40_model_bundle(
            repo_root=repo_root,
            comparison_run=run,
            expected_role=role,
        )
        for role, run in zip(("qwen", "phobert"), comparison.runs, strict=True)
    )
    if (
        models[0].selected_checkpoint_identity
        != production_values.get("qwen_selected_checkpoint_identity")
        or models[1].selected_checkpoint_identity
        != production_values.get("phobert_selected_checkpoint_identity")
        or models[1].artifact_sha256
        != production_values.get("phobert_selected_artifact_sha256")
    ):
        raise ContractError(
            "Phase 40 model identities differ from fixed portable authorities"
        )

    from src.model_adaptation.phase40_review import (
        read_phase40_review_regular_bytes,
    )

    try:
        review_bytes = read_phase40_review_regular_bytes(
            review_path,
            description="Phase 40 human-review manifest",
        )
    except ValueError as exc:
        raise ContractError(
            "Phase 40 human-review manifest is missing or unsafe"
        ) from exc
    review = _parse_json_bytes(review_bytes, "Phase 40 human-review manifest")
    if review_bytes != _canonical_json_bytes(review):
        raise ContractError("Phase 40 human-review manifest is not canonical JSON")
    base_review_fields = {
        "schema_version",
        "vietnamese_fluent_attestation",
        "rows",
        "queue_sha256",
        "reviewer_return_sha256",
        "notes_sha256",
        "report_sha256",
        "comparison_manifest_sha256",
        "scope_amendment_sha256",
        "review_queue_manifest_sha256",
        "phase39_data_contract_sha256",
        "validation_ordered_row_ids_sha256",
        "frozen_results_sha256",
        "summary",
        "limitations",
    }
    lineage_review_fields = {
        "superseded_scope_amendment_sha256",
        "final_comparison_authority_sha256",
    }
    review_schema = review.get("schema_version")
    if review_schema == "phase40-human-review-v2":
        expected_review_fields = base_review_fields
    elif review_schema == "phase40-human-review-v3":
        expected_review_fields = base_review_fields | lineage_review_fields
    else:
        raise ContractError("Phase 40 human-review schema is unsupported")
    hash_fields = expected_review_fields.difference(
        {
            "schema_version",
            "vietnamese_fluent_attestation",
            "rows",
            "summary",
            "limitations",
        }
    )
    for field in hash_fields:
        _require_sha256(review.get(field), f"Phase 40 review {field}")
    if (
        set(review) != expected_review_fields
        or review["vietnamese_fluent_attestation"] is not True
        or review["rows"] != comparison.review_queue_rows
        or review["queue_sha256"] != comparison.review_queue_sha256
        or review["comparison_manifest_sha256"] != _sha256(comparison_bytes)
        or review["scope_amendment_sha256"] != comparison.scope_amendment_sha256
        or review["phase39_data_contract_sha256"] != phase39_contract_identity
        or review["limitations"] != list(comparison.limitations)
        or not isinstance(review["summary"], dict)
        or not review["summary"]
    ):
        raise ContractError("Phase 40 human-review closure drifted")
    if review_schema == "phase40-human-review-v3" and (
        review["superseded_scope_amendment_sha256"]
        != comparison.superseded_scope_amendment_sha256
        or review["final_comparison_authority_sha256"]
        != comparison.final_comparison_authority_sha256
    ):
        raise ContractError("Phase 40 human-review v3 lineage drifted")

    review_side_paths = {
        "reviewer_return_sha256": review_path.with_name("reviewer-return.jsonl"),
        "notes_sha256": review_path.with_name("human-review-notes.jsonl"),
        "report_sha256": review_path.with_name("human-review-report.md"),
    }
    try:
        review_side_bytes = {
            field: read_phase40_review_regular_bytes(
                path,
                description=f"Phase 40 {field.removesuffix('_sha256')}",
            )
            for field, path in review_side_paths.items()
        }
    except ValueError as exc:
        raise ContractError("Phase 40 human-review side artifact is missing or unsafe") from exc
    if any(
        _sha256(review_side_bytes[field]) != review[field]
        for field in review_side_paths
    ):
        raise ContractError("Phase 40 human-review side artifact hash drifted")
    return (
        (models[0], models[1]),
        _sha256(comparison_bytes),
        _sha256(review_bytes),
    )


def _discover_phase41_production_roots(
    *,
    repo_root: Path,
    models: Sequence[FrozenModelIdentity],
) -> tuple[Path, Path, Path, Path, object]:
    """Locate external bytes by receipt hashes, then run the full Phase 40 closure."""

    from src.model_adaptation.phase40_production_authorities import (
        EXTERNAL_MODELS_PORTABLE_RUNTIME,
        VerifiedPhase40ProductionAuthorities,
        verify_phase40_production_authorities,
    )

    repository_qwen_bundle = (
        Path(repo_root) / "data/models/phase40/full/qwen-qlora/adapter-or-model"
    )
    adapter_config_path = repository_qwen_bundle / "adapter_config.json"
    if not adapter_config_path.is_file() or adapter_config_path.is_symlink():
        raise ContractError("Phase 40 Qwen adapter configuration is missing or unsafe")
    adapter_config = _parse_json_bytes(
        adapter_config_path.read_bytes(), "Phase 40 Qwen adapter configuration"
    )
    qwen_base = Path(str(adapter_config.get("base_model_name_or_path", "")))
    if not qwen_base.is_absolute() or qwen_base.parent == qwen_base:
        raise ContractError("Phase 40 Qwen local base-model root is not absolute")
    transfer_roots = tuple(
        parent for parent in qwen_base.parents if parent.name.startswith("transfer-root-")
    )
    if len(transfer_roots) != 1:
        raise ContractError("Phase 40 external transfer root is ambiguous")
    transfer_root = transfer_roots[0]
    package_root = transfer_root.parent
    qwen_bundle = (
        transfer_root / "data/models/phase40/full/qwen-qlora/adapter-or-model"
    )

    qwen_receipt, _ = _load_canonical_json(
        Path(repo_root) / "data/models/phase40/qwen-gguf-verification-receipt.json",
        "Phase 40 Qwen GGUF verification receipt",
    )
    phobert_receipt, _ = _load_canonical_json(
        Path(repo_root) / "data/models/phase40/phobert-tokenizer-authority.json",
        "Phase 40 PhoBERT release receipt",
    )
    qwen_export = qwen_receipt.get("export")
    if not isinstance(qwen_export, dict):
        raise ContractError("Phase 40 Qwen GGUF receipt export authority is missing")
    qwen_manifest_sha = _require_sha256(
        qwen_export.get("manifest_sha256"), "Phase 40 Qwen export manifest"
    )
    phobert_manifest_sha = _require_sha256(
        phobert_receipt.get("bundle_manifest_sha256"),
        "Phase 40 PhoBERT bundle manifest",
    )
    if not package_root.is_dir() or package_root.is_symlink():
        raise ContractError("Phase 40 external package root is missing or unsafe")
    qwen_candidates: list[Path] = []
    phobert_candidates: list[Path] = []
    for child in package_root.iterdir():
        if not child.is_dir() or child.is_symlink():
            continue
        qwen_manifest = child / "qwen-qlora-q8_0.gguf.manifest.json"
        if (
            qwen_manifest.is_file()
            and not qwen_manifest.is_symlink()
            and _sha256(qwen_manifest.read_bytes()) == qwen_manifest_sha
        ):
            qwen_candidates.append(child)
        phobert_manifest = (
            child
            / "data/models/phase40/inference/phobert/phobert-release-manifest.json"
        )
        if (
            phobert_manifest.is_file()
            and not phobert_manifest.is_symlink()
            and _sha256(phobert_manifest.read_bytes()) == phobert_manifest_sha
        ):
            phobert_candidates.append(child)
    if len(qwen_candidates) != 1 or len(phobert_candidates) != 1:
        raise ContractError("Phase 40 external receipt-bound roots are missing or ambiguous")
    phobert_provenance, _ = _load_canonical_json(
        phobert_candidates[0]
        / "data/models/phase40/inference/phobert/model-artifact/"
        "phase40-base-model-provenance.json",
        "Phase 40 PhoBERT base-model provenance",
    )
    expected_phobert_path_sha = _require_sha256(
        phobert_provenance.get("local_path_sha256"),
        "Phase 40 PhoBERT local base path",
    )
    phobert_base_candidates: list[Path] = []
    for child in package_root.iterdir():
        if not child.name.startswith("transfer-root"):
            continue
        candidate = child / "data/models/phase40/base/phobert-base-v2"
        if not candidate.is_dir() or candidate.is_symlink():
            continue
        normalized = os.path.normcase(
            os.fspath(Path(os.path.abspath(os.path.normpath(os.fspath(candidate)))))
        ).replace("\\", "/")
        path_sha = _sha256(
            b"phase40-phobert-local-base-path-v1\0"
            + normalized.encode("utf-8", errors="strict")
        )
        if path_sha == expected_phobert_path_sha:
            phobert_base_candidates.append(candidate)
    if len(phobert_base_candidates) != 1:
        raise ContractError("Phase 40 PhoBERT base-model root is missing or ambiguous")
    phobert_base = phobert_base_candidates[0]
    try:
        production = verify_phase40_production_authorities(
            repo_root=Path(repo_root),
            qwen_export_root=qwen_candidates[0],
            phobert_transfer_root=phobert_candidates[0],
        )
    except Exception as exc:
        raise ContractError("Phase 40 live production authority closure failed") from exc
    if (
        type(production) is not VerifiedPhase40ProductionAuthorities
        or production.verification_mode != EXTERNAL_MODELS_PORTABLE_RUNTIME
        or production.qwen_selected_checkpoint_identity
        != models[0].selected_checkpoint_identity
        or production.phobert_selected_checkpoint_identity
        != models[1].selected_checkpoint_identity
        or production.phobert_selected_artifact_sha256 != models[1].artifact_sha256
    ):
        raise ContractError("Phase 40 live production identities differ from comparison")
    phobert_bundle = (
        phobert_candidates[0] / "data/models/phase40/inference/phobert"
    )
    return qwen_bundle, qwen_base, phobert_bundle, phobert_base, production


def prepare_phase41_from_canonical_authorities(
    output_root: Path,
    *,
    repo_root: Path,
    phase39_contract_path: Path,
    phase40_comparison_manifest_path: Path,
    phase40_review_manifest_path: Path,
) -> PreparedPhase41Evaluation:
    """Freeze the one canonical zero-access production preparation."""

    repository = Path(os.path.abspath(os.path.normpath(os.fspath(repo_root))))
    phase39_path = _code_fixed_authority_path(
        repository,
        phase39_contract_path,
        _PHASE39_AUTHORITY_RELATIVE,
        "Phase 39 downstream authority",
    )
    comparison_path = _code_fixed_authority_path(
        repository,
        phase40_comparison_manifest_path,
        _PHASE40_COMPARISON_RELATIVE,
        "Phase 40 comparison manifest",
    )
    review_path = _code_fixed_authority_path(
        repository,
        phase40_review_manifest_path,
        _PHASE40_REVIEW_RELATIVE,
        "Phase 40 human-review manifest",
    )
    held_out, phase39_identity = _phase39_opaque_authority(
        phase39_path, repo_root=repository
    )
    models, comparison_sha, review_sha = _verify_phase40_closure(
        repo_root=repository,
        comparison_path=comparison_path,
        review_path=review_path,
        phase39_contract_identity=phase39_identity,
    )
    comparison, _ = _load_canonical_json(
        comparison_path, "Phase 40 comparison manifest"
    )
    qwen_bundle, qwen_base, phobert_bundle, phobert_base, production = (
        _discover_phase41_production_roots(repo_root=repository, models=models)
    )
    production_values = production.as_dict()
    if any(
        comparison.get(name) != production_values.get(name)
        for name in (
            "comparison_launch_receipt_sha256",
            *_PHASE40_REQUIRED_AUTHORITY_HASH_FIELDS,
        )
    ):
        raise ContractError("Phase 40 live authorities differ from the final comparison")

    from src.model_adaptation.phase41_protocols import (
        build_production_protocol_authority,
        run_phase41_preauthorization_smokes,
        write_protocol_authority,
    )

    protocols = build_production_protocol_authority(
        repo_root=repository,
        qwen_bundle_root=qwen_bundle,
        qwen_base_root=qwen_base,
        phobert_bundle_root=phobert_bundle,
        phobert_base_root=phobert_base,
        models=models,
    )
    root = Path(output_root)
    if root.exists():
        if not root.is_dir() or root.is_symlink() or tuple(root.iterdir()):
            raise ContractError("Phase 41 production output root must be an empty directory")
    else:
        root.mkdir(parents=True, exist_ok=False)
    protocol_path = write_protocol_authority(root, protocols)
    protocol_bytes = protocol_path.read_bytes()
    _, source_sha = _write_source_manifest(
        root,
        _require_sha256(
            comparison.get("comparison_finalizer_source_sha256"),
            "Phase 40 comparison finalizer source",
        ),
        preparation_scope=PRODUCTION_PREPARATION_SCOPE,
        repository_root=repository,
        comparison_launch_receipt_sha256=str(
            comparison["comparison_launch_receipt_sha256"]
        ),
    )
    registry = _claim_registry_authority(_provision_claim_registry_root())
    model_smokes = tuple(run_phase41_preauthorization_smokes(root))
    model_smokes_sha = _sha256(_canonical_json_bytes(model_smokes))
    bundle_authorities = [
        {
            "role": protocol.role,
            "bundle_root": protocol.body["bundle_root"],
            "bundle_root_sha256": protocol.body["bundle_root_sha256"],
        }
        for protocol in (protocols.qwen, protocols.phobert)
    ]
    authorities: dict[str, object] = {
        "protocols_sha256": _sha256(protocol_bytes),
        "model_bundle_authorities": bundle_authorities,
        "execution_source_manifest_sha256": source_sha,
        "comparison_authority_sha256": comparison_sha,
        "review_closure_sha256": review_sha,
        "comparison_launch_receipt_sha256": production_values[
            "comparison_launch_receipt_sha256"
        ],
        **{
            name: production_values[name]
            for name in _PHASE40_REQUIRED_AUTHORITY_HASH_FIELDS
        },
        "prior_human_exposure_disclosed": True,
        "phase39_contract_file_sha256": _sha256(phase39_path.read_bytes()),
        "phase39_data_contract_sha256": phase39_identity,
        "scope_amendment_sha256": _require_sha256(
            comparison.get("scope_amendment_sha256"), "Phase 40 scope amendment"
        ),
        "superseded_scope_amendment_sha256": _require_sha256(
            comparison.get("superseded_scope_amendment_sha256"),
            "Phase 40 superseded scope amendment",
        ),
        "final_comparison_authority_sha256": _require_sha256(
            comparison.get("final_comparison_authority_sha256"),
            "Phase 40 final comparison authority",
        ),
        "comparison_finalizer_source_sha256": _require_sha256(
            comparison.get("comparison_finalizer_source_sha256"),
            "Phase 40 comparison finalizer source",
        ),
        "claim_registry_authority_sha256": registry["authority_sha256"],
        "model_smokes_sha256": model_smokes_sha,
    }
    request_path = _freeze_evaluation_request(
        root,
        reserved_split_path=held_out.path,
        expected_records=held_out.records,
        expected_bytes=held_out.bytes,
        expected_sha256=held_out.sha256,
        expected_label_counts=dict(held_out.label_counts),
        models=models,
        deployment_fit_choice=PENDING_DEPLOYMENT_FIT_CHOICE,
        preparation_scope=PRODUCTION_PREPARATION_SCOPE,
        authorities=authorities,
    )
    request_bytes = request_path.read_bytes()
    receipt = _production_preauthorization_record(
        request=_parse_json_bytes(request_bytes, "Phase 41 evaluation request"),
        request_bytes=request_bytes,
        authorities=authorities,
        model_smokes=model_smokes,
        claim_registry=registry,
    )
    _exclusive_write(
        root / PREAUTHORIZATION_NAME, _canonical_json_bytes(receipt)
    )
    return verify_phase41_preauthorization(root)


__all__ = [
    "AlreadySpentError",
    "AUTHORIZED_POST_EVALUATION_FIT_SIGNAL",
    "AuthorizationError",
    "ContractError",
    "DEFERRED_AUTHORIZATION_SIGNAL",
    "DeploymentFitDisposition",
    "FrozenModelIdentity",
    "InMemorySnapshot",
    "LABEL_ORDER",
    "ModelIdentity",
    "OpaqueHeldOutAuthority",
    "PREDICTION_COLUMNS",
    "PHASE41_PRODUCTION_BOOTSTRAP_REQUIRED",
    "Phase41EvidenceManifest",
    "Prediction",
    "PreparedPhase41Evaluation",
    "authorize_phase41_evaluation",
    "comparison_statements",
    "compute_metrics",
    "freeze_deployment_fit_disposition",
    "prepare_phase41_from_canonical_authorities",
    "run_phase41_once",
    "selected_phase41_checkpoint_identities",
    "verify_phase41_evidence",
    "verify_phase41_preauthorization",
]
