[CmdletBinding()]
param(
    [string]$OutputRoot
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
if ([string]::IsNullOrWhiteSpace($OutputRoot)) {
    throw "OutputRoot is required"
}

function Open-LockedReadFile {
    param([Parameter(Mandatory = $true)][string]$LiteralPath)

    $Resolved = [System.IO.Path]::GetFullPath($LiteralPath)
    $Attributes = [System.IO.File]::GetAttributes($Resolved)
    if (($Attributes -band [System.IO.FileAttributes]::Directory) -ne 0 -or
        ($Attributes -band [System.IO.FileAttributes]::ReparsePoint) -ne 0) {
        throw "Locked authority must be a regular non-reparse file: $Resolved"
    }
    $Stream = [System.IO.File]::Open(
        $Resolved,
        [System.IO.FileMode]::Open,
        [System.IO.FileAccess]::Read,
        [System.IO.FileShare]::Read
    )
    try {
        $Hasher = [System.Security.Cryptography.SHA256]::Create()
        try {
            $Digest = ([System.BitConverter]::ToString(
                $Hasher.ComputeHash($Stream)
            )).Replace('-', '').ToLowerInvariant()
        }
        finally {
            $Hasher.Dispose()
        }
        $Stream.Position = 0
        return [PSCustomObject]@{
            Path = $Resolved
            Stream = $Stream
            Bytes = [long]$Stream.Length
            Sha256 = $Digest
        }
    }
    catch {
        $Stream.Dispose()
        throw
    }
}

function Assert-NonReparseDirectoryChain {
    param(
        [Parameter(Mandatory = $true)][string]$Root,
        [Parameter(Mandatory = $true)][string]$Leaf
    )

    $ResolvedRoot = [System.IO.Path]::GetFullPath($Root).TrimEnd('\')
    $ResolvedLeaf = [System.IO.Path]::GetFullPath($Leaf).TrimEnd('\')
    $Prefix = $ResolvedRoot + '\'
    if ($ResolvedLeaf -cne $ResolvedRoot -and
        -not $ResolvedLeaf.StartsWith($Prefix, [StringComparison]::OrdinalIgnoreCase)) {
        throw "Directory chain escaped its fixed root"
    }
    $Current = [System.IO.DirectoryInfo]::new($ResolvedLeaf)
    while ($null -ne $Current) {
        if (-not $Current.Exists) {
            throw "Required directory is absent: $($Current.FullName)"
        }
        if (($Current.Attributes -band [System.IO.FileAttributes]::ReparsePoint) -ne 0) {
            throw "Required directory chain contains a reparse point: $($Current.FullName)"
        }
        if ($Current.FullName.TrimEnd('\') -ieq $ResolvedRoot) {
            return
        }
        $Current = $Current.Parent
    }
    throw "Directory chain did not reach its fixed root"
}

function Assert-NoReparseDirectoryAncestors {
    param([Parameter(Mandatory = $true)][string]$DirectoryPath)

    $Current = [System.IO.DirectoryInfo]::new(
        [System.IO.Path]::GetFullPath($DirectoryPath)
    )
    while ($null -ne $Current) {
        if (-not $Current.Exists) {
            throw "Required directory ancestor is absent: $($Current.FullName)"
        }
        if (($Current.Attributes -band [System.IO.FileAttributes]::ReparsePoint) -ne 0) {
            throw "Required directory ancestry contains a reparse point: $($Current.FullName)"
        }
        $Current = $Current.Parent
    }
}

function Assert-ProtectedRegistryAcl {
    param([Parameter(Mandatory = $true)][string]$RegistryPath)

    $OperatorSid = [System.Security.Principal.WindowsIdentity]::GetCurrent().User.Value
    $Allowed = [System.Collections.Generic.HashSet[string]]::new(
        [StringComparer]::OrdinalIgnoreCase
    )
    foreach ($Sid in @($OperatorSid, 'S-1-5-18', 'S-1-5-32-544')) {
        [void]$Allowed.Add($Sid)
    }
    $Acl = Get-Acl -LiteralPath $RegistryPath
    if (-not $Acl.AreAccessRulesProtected) {
        throw "Protected Phase 41 claim registry must disable inherited DACL rules"
    }
    try {
        $OwnerSid = [System.Security.Principal.SecurityIdentifier]::new(
            [string]$Acl.Owner
        ).Value
    }
    catch {
        $OwnerSid = [System.Security.Principal.NTAccount]::new(
            [string]$Acl.Owner
        ).Translate([System.Security.Principal.SecurityIdentifier]).Value
    }
    if (-not $Allowed.Contains($OwnerSid)) {
        throw "Protected Phase 41 claim registry has an untrusted owner"
    }
    $ObservedWriters = [System.Collections.Generic.HashSet[string]]::new(
        [StringComparer]::OrdinalIgnoreCase
    )
    $WriteMask = [int64](
        [System.Security.AccessControl.FileSystemRights]::Write -bor
        [System.Security.AccessControl.FileSystemRights]::Modify -bor
        [System.Security.AccessControl.FileSystemRights]::Delete -bor
        [System.Security.AccessControl.FileSystemRights]::ChangePermissions -bor
        [System.Security.AccessControl.FileSystemRights]::TakeOwnership -bor
        [System.Security.AccessControl.FileSystemRights]::CreateFiles -bor
        [System.Security.AccessControl.FileSystemRights]::CreateDirectories -bor
        [System.Security.AccessControl.FileSystemRights]::DeleteSubdirectoriesAndFiles
    )
    foreach ($Rule in $Acl.Access) {
        if ($Rule.IsInherited) {
            throw "Protected Phase 41 claim registry contains an inherited ACE"
        }
        $Sid = $Rule.IdentityReference.Translate(
            [System.Security.Principal.SecurityIdentifier]
        ).Value
        $Writes = (([int64]$Rule.FileSystemRights -band $WriteMask) -ne 0)
        if (-not $Writes) {
            continue
        }
        if ($Rule.AccessControlType -eq [System.Security.AccessControl.AccessControlType]::Allow) {
            if (-not $Allowed.Contains($Sid)) {
                throw "Protected Phase 41 claim registry grants write control to another SID"
            }
            [void]$ObservedWriters.Add($Sid)
        }
        elseif ($Allowed.Contains($Sid)) {
            throw "Protected Phase 41 claim registry denies a required writer"
        }
    }
    if ($ObservedWriters.Count -ne $Allowed.Count) {
        throw "Protected Phase 41 claim registry required writer grants are incomplete"
    }
}

$ResolvedOutput = [System.IO.Path]::GetFullPath($OutputRoot)
if (-not [System.IO.Directory]::Exists($ResolvedOutput)) {
    throw "OutputRoot must already contain the frozen Phase 41 authorities"
}
$OutputAttributes = [System.IO.File]::GetAttributes($ResolvedOutput)
if (($OutputAttributes -band [System.IO.FileAttributes]::ReparsePoint) -ne 0) {
    throw "OutputRoot cannot be a reparse point"
}
Assert-NoReparseDirectoryAncestors -DirectoryPath $ResolvedOutput

# Use the Windows Known Folder identity, never the mutable ProgramData
# environment variable. Python independently repeats this exact check.
$ProgramDataRoot = [Environment]::GetFolderPath(
    [Environment+SpecialFolder]::CommonApplicationData
)
if ([string]::IsNullOrWhiteSpace($ProgramDataRoot)) {
    throw "Windows CommonApplicationData identity is unavailable"
}
$ExpectedOperationalRoot = [System.IO.Path]::GetFullPath(
    (Join-Path $ProgramDataRoot "VNPhish\phase41-evaluation-evidence")
)
if (-not [string]::Equals(
    $ResolvedOutput.TrimEnd([System.IO.Path]::DirectorySeparatorChar),
    $ExpectedOperationalRoot.TrimEnd([System.IO.Path]::DirectorySeparatorChar),
    [System.StringComparison]::OrdinalIgnoreCase
)) {
    throw "OutputRoot differs from the fixed operational evidence root"
}
Assert-ProtectedRegistryAcl -RegistryPath $ResolvedOutput
$ClaimRegistry = Join-Path $ProgramDataRoot "VNPhish\phase41-one-shot-claims"
Assert-NoReparseDirectoryAncestors -DirectoryPath $ProgramDataRoot
$ProtectedParent = Join-Path $ProgramDataRoot "VNPhish"
Assert-ProtectedRegistryAcl -RegistryPath $ProtectedParent
Assert-NonReparseDirectoryChain -Root $ProgramDataRoot -Leaf $ClaimRegistry
Assert-ProtectedRegistryAcl -RegistryPath $ClaimRegistry

$LauncherPath = [System.IO.Path]::GetFullPath($MyInvocation.MyCommand.Path)
if ([System.IO.Path]::GetFileName($LauncherPath) -cne "phase41_one_shot_launcher.ps1") {
    throw "Launcher filename drifted"
}
$RepositoryRoot = [System.IO.Directory]::GetParent(
    [System.IO.Directory]::GetParent($LauncherPath).FullName
).FullName
if (-not [string]::Equals(
    $RepositoryRoot.TrimEnd([System.IO.Path]::DirectorySeparatorChar),
    $ResolvedOutput.TrimEnd([System.IO.Path]::DirectorySeparatorChar),
    [System.StringComparison]::OrdinalIgnoreCase
)) {
    throw "Staged launcher root differs from the operational evidence root"
}
Assert-NoReparseDirectoryAncestors -DirectoryPath $RepositoryRoot

$AuthorityLocks = [System.Collections.Generic.List[System.IDisposable]]::new()
$SourceLocks = [System.Collections.Generic.List[System.IDisposable]]::new()
$CleanLocks = [System.Collections.Generic.List[System.IDisposable]]::new()
$OldPythonPath = $env:PYTHONPATH
$OldPythonHome = $env:PYTHONHOME
$OldNoUserSite = $env:PYTHONNOUSERSITE
try {
    $LauncherLock = Open-LockedReadFile -LiteralPath $LauncherPath
    $AuthorityLocks.Add($LauncherLock.Stream)
    $LauncherProcess = Get-Process -Id $PID
    $LauncherImagePath = [System.IO.Path]::GetFullPath(
        $LauncherProcess.MainModule.FileName
    )
    Assert-NoReparseDirectoryAncestors -DirectoryPath (
        [System.IO.Path]::GetDirectoryName($LauncherImagePath)
    )
    $LauncherImageLock = Open-LockedReadFile -LiteralPath $LauncherImagePath
    $AuthorityLocks.Add($LauncherImageLock.Stream)

    $SourceManifest = Join-Path $ResolvedOutput "execution-source-manifest.json"
    $ProtocolAuthority = Join-Path $ResolvedOutput "frozen-inference-protocols.json"
    $PreparedRequest = Join-Path $ResolvedOutput "evaluation-request.json"
    $Preauthorization = Join-Path $ResolvedOutput "preauthorization-receipt.json"
    $Authorization = Join-Path $ResolvedOutput "one-shot-authorization.json"
    $LockedAuthorities = @{}
    foreach ($RequiredPath in @(
        $SourceManifest,
        $ProtocolAuthority,
        $PreparedRequest,
        $Preauthorization,
        $Authorization
    )) {
        $Locked = Open-LockedReadFile -LiteralPath $RequiredPath
        $AuthorityLocks.Add($Locked.Stream)
        $LockedAuthorities[$RequiredPath] = $Locked
    }

    $Manifest = Get-Content -Raw -LiteralPath $SourceManifest | ConvertFrom-Json
    $Request = Get-Content -Raw -LiteralPath $PreparedRequest | ConvertFrom-Json
    if ($Manifest.schema_version -cne "phase41-execution-source-manifest-v1") {
        throw "Execution source manifest schema drifted"
    }
    if ([string]$Manifest.preparation_scope -cne "production_canonical" -or
        [string]$Request.preparation_scope -cne "production_canonical") {
        throw "Protected launcher accepts only canonical production preparation"
    }
    if ([string]$Manifest.launcher_host.mode -cne "phase40_external_launcher_authority" -or
        [string]$Manifest.launcher_host.external_launch_receipt_sha256 -cne
            [string]$Request.authorities.comparison_launch_receipt_sha256 -or
        [System.IO.Path]::GetFullPath([string]$Manifest.launcher_host.path) -cne
            $LauncherImagePath -or
        [long]$Manifest.launcher_host.bytes -ne $LauncherImageLock.Bytes -or
        [string]$Manifest.launcher_host.sha256 -cne $LauncherImageLock.Sha256) {
        throw "PowerShell launcher host differs from the precommitted source authority"
    }
    if ($Manifest.launcher.path -cne "scripts/phase41_one_shot_launcher.ps1" -or
        [long]$Manifest.launcher.bytes -ne $LauncherLock.Bytes -or
        [string]$Manifest.launcher.sha256 -cne $LauncherLock.Sha256) {
        throw "Launcher bytes differ from the execution source authority"
    }
    if ([string]$Request.authorities.protocols_sha256 -cne
        $LockedAuthorities[$ProtocolAuthority].Sha256) {
        throw "Protocol bytes differ from the prepared request"
    }
    foreach ($AuthorityField in @(
        "qwen_gguf_verification_receipt_sha256",
        "phobert_release_receipt_authority_sha256",
        "phobert_segmenter_authority_sha256",
        "runtime_dependency_authority_sha256",
        "runtime_materialization_receipt_sha256"
    )) {
        if ([string]$Request.authorities.$AuthorityField -cnotmatch "^[0-9a-f]{64}$") {
            throw "Required Phase 40 authority digest is absent: $AuthorityField"
        }
    }

    $PythonPath = [System.IO.Path]::GetFullPath([string]$Manifest.python.path)
    $PythonLock = Open-LockedReadFile -LiteralPath $PythonPath
    $AuthorityLocks.Add($PythonLock.Stream)
    Assert-NoReparseDirectoryAncestors -DirectoryPath (
        [System.IO.Path]::GetDirectoryName($PythonPath)
    )
    if ([long]$Manifest.python.bytes -ne $PythonLock.Bytes -or
        [string]$Manifest.python.sha256 -cne $PythonLock.Sha256) {
        throw "Pinned Python executable bytes drifted"
    }
    foreach ($ImportRoot in $Manifest.python.runtime_import_roots) {
        $ResolvedImportRoot = [System.IO.Path]::GetFullPath([string]$ImportRoot)
        if (-not [System.IO.Directory]::Exists($ResolvedImportRoot)) {
            throw "Pinned runtime import root is absent"
        }
        Assert-NoReparseDirectoryAncestors -DirectoryPath $ResolvedImportRoot
        $ImportAttributes = [System.IO.File]::GetAttributes($ResolvedImportRoot)
        if (($ImportAttributes -band [System.IO.FileAttributes]::ReparsePoint) -ne 0) {
            throw "Pinned runtime import root cannot be a reparse point"
        }
    }

    $CleanRoot = Join-Path $ResolvedOutput "clean-runtime"
    if ([System.IO.File]::Exists($CleanRoot) -or
        [System.IO.Directory]::Exists($CleanRoot)) {
        throw "Reviewed clean runtime must be freshly materialized"
    }
    [void][System.IO.Directory]::CreateDirectory($CleanRoot)
    $CleanPrefix = $CleanRoot.TrimEnd('\') + '\'
    $ExpectedSourcePaths = [System.Collections.Generic.HashSet[string]]::new(
        [StringComparer]::Ordinal
    )
    foreach ($SourceFile in $Manifest.files) {
        $RelativePath = ([string]$SourceFile.path).Replace('\', '/')
        if ([System.IO.Path]::IsPathRooted($RelativePath) -or
            $RelativePath.Split('/') -contains '..' -or
            -not $ExpectedSourcePaths.Add($RelativePath)) {
            throw "Execution source inventory path escaped or duplicated"
        }
        $SourcePath = [System.IO.Path]::GetFullPath((Join-Path $RepositoryRoot $RelativePath))
        $RepositoryPrefix = $RepositoryRoot.TrimEnd('\') + '\'
        if (-not $SourcePath.StartsWith($RepositoryPrefix, [StringComparison]::OrdinalIgnoreCase)) {
            throw "Execution source path escaped the repository"
        }
        Assert-NonReparseDirectoryChain `
            -Root $RepositoryRoot `
            -Leaf ([System.IO.Path]::GetDirectoryName($SourcePath))
        $SourceLock = Open-LockedReadFile -LiteralPath $SourcePath
        $SourceLocks.Add($SourceLock.Stream)
        if ($SourceLock.Bytes -ne [long]$SourceFile.bytes -or
            $SourceLock.Sha256 -cne [string]$SourceFile.sha256) {
            throw "Execution source bytes drifted: $RelativePath"
        }
        $Destination = [System.IO.Path]::GetFullPath((Join-Path $CleanRoot $RelativePath))
        if (-not $Destination.StartsWith($CleanPrefix, [StringComparison]::OrdinalIgnoreCase)) {
            throw "Clean-runtime destination escaped"
        }
        [void][System.IO.Directory]::CreateDirectory(
            [System.IO.Path]::GetDirectoryName($Destination)
        )
        Assert-NonReparseDirectoryChain `
            -Root $CleanRoot `
            -Leaf ([System.IO.Path]::GetDirectoryName($Destination))
        $Writer = [System.IO.File]::Open(
            $Destination,
            [System.IO.FileMode]::CreateNew,
            [System.IO.FileAccess]::Write,
            [System.IO.FileShare]::None
        )
        try {
            $SourceLock.Stream.Position = 0
            $SourceLock.Stream.CopyTo($Writer)
            $Writer.Flush($true)
        }
        finally {
            $Writer.Dispose()
        }
        $CleanLock = Open-LockedReadFile -LiteralPath $Destination
        $CleanLocks.Add($CleanLock.Stream)
        if ($CleanLock.Bytes -ne [long]$SourceFile.bytes -or
            $CleanLock.Sha256 -cne [string]$SourceFile.sha256) {
            throw "Materialized clean source bytes drifted: $RelativePath"
        }
    }
    foreach ($Directory in Get-ChildItem -LiteralPath $CleanRoot -Directory -Recurse -Force) {
        if (($Directory.Attributes -band [System.IO.FileAttributes]::ReparsePoint) -ne 0) {
            throw "Clean runtime contains an unbound reparse directory"
        }
    }
    $ActualSourcePaths = @(
        Get-ChildItem -LiteralPath $CleanRoot -File -Recurse -Force | ForEach-Object {
            $_.FullName.Substring($CleanPrefix.Length).Replace('\', '/')
        }
    )
    if ($ActualSourcePaths.Count -ne $ExpectedSourcePaths.Count) {
        throw "Clean runtime file set differs from the execution source inventory"
    }
    foreach ($ActualPath in $ActualSourcePaths) {
        if (-not $ExpectedSourcePaths.Contains($ActualPath)) {
            throw "Clean runtime contains an unbound source file: $ActualPath"
        }
    }

    Remove-Item Env:PYTHONPATH -ErrorAction SilentlyContinue
    Remove-Item Env:PYTHONHOME -ErrorAction SilentlyContinue
    $env:PYTHONNOUSERSITE = "1"
    $CapabilityBytes = [byte[]]::new(32)
    [System.Security.Cryptography.RandomNumberGenerator]::Fill($CapabilityBytes)
    $CapabilityHasher = [System.Security.Cryptography.SHA256]::Create()
    try {
        $CapabilitySha256 = ([System.BitConverter]::ToString(
            $CapabilityHasher.ComputeHash($CapabilityBytes)
        )).Replace('-', '').ToLowerInvariant()
    }
    finally {
        $CapabilityHasher.Dispose()
    }
    $MaterializationReceipt = Join-Path $ResolvedOutput "execution-materialization-receipt.json"
    if ([System.IO.File]::Exists($MaterializationReceipt)) {
        throw "Execution materialization receipt already exists"
    }
    $ReceiptBuilder = @'
from datetime import datetime, timezone
import hashlib
import json
import os
import platform
from pathlib import Path
import sys

def reject_duplicates(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise RuntimeError(f"duplicate JSON key: {key}")
        result[key] = value
    return result

def canonical(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n").encode("utf-8")

def load(path):
    payload = Path(path).read_bytes()
    value = json.loads(payload.decode("utf-8", errors="strict"), object_pairs_hook=reject_duplicates, parse_constant=lambda value: (_ for _ in ()).throw(RuntimeError(value)))
    if payload != canonical(value):
        raise RuntimeError("authority is not canonical JSON")
    return value, payload

(
    receipt_path,
    source_path,
    request_path,
    protocol_path,
    clean_root,
    launcher_capability_sha256,
    launcher_process_id_raw,
    launcher_process_image_path,
    launcher_process_image_sha256,
) = sys.argv[1:]
source, source_bytes = load(source_path)
request, _ = load(request_path)
_, protocol_bytes = load(protocol_path)
scope = source.get("preparation_scope")
if scope not in {"production_canonical", "synthetic_test"} or request.get("preparation_scope") != scope:
    raise RuntimeError("request/source preparation scope drifted")
if platform.python_version() != source["python"]["version"]:
    raise RuntimeError("pinned Python version drifted")
if len(launcher_capability_sha256) != 64 or any(
    value not in "0123456789abcdef" for value in launcher_capability_sha256
):
    raise RuntimeError("launcher capability digest is invalid")
launcher_process_id = int(launcher_process_id_raw)
if launcher_process_id <= 0:
    raise RuntimeError("launcher process identity is invalid")
normalized_launcher_image = os.path.normcase(
    os.path.abspath(os.path.normpath(launcher_process_image_path))
)
launcher_host = source.get("launcher_host")
if not isinstance(launcher_host, dict) or launcher_host.get("mode") != (
    "phase40_external_launcher_authority" if scope == "production_canonical" else "synthetic_test"
):
    raise RuntimeError("launcher host authority mode drifted")
external_launcher_authority_sha256 = (
    launcher_host.get("external_launch_receipt_sha256")
    if scope == "production_canonical"
    else "0" * 64
)
if scope == "production_canonical" and external_launcher_authority_sha256 != request["authorities"].get("comparison_launch_receipt_sha256"):
    raise RuntimeError("external launcher authority differs from prepared request")
normalized_authorized_host = os.path.normcase(
    os.path.abspath(os.path.normpath(str(launcher_host.get("path", ""))))
)
launcher_image_bytes = Path(normalized_launcher_image).read_bytes()
if (
    normalized_launcher_image != normalized_authorized_host
    or launcher_host.get("bytes") != len(launcher_image_bytes)
    or launcher_host.get("sha256") != hashlib.sha256(launcher_image_bytes).hexdigest()
    or launcher_process_image_sha256 != launcher_host.get("sha256")
):
    raise RuntimeError("launcher host differs from the precommitted authority")
if len(launcher_process_image_sha256) != 64 or any(
    value not in "0123456789abcdef" for value in launcher_process_image_sha256
):
    raise RuntimeError("launcher process image digest is invalid")
bundle_bytes = canonical(request["authorities"]["model_bundle_authorities"])
required_phase40_authorities = {
    name: request["authorities"].get(name)
    for name in (
        "qwen_gguf_verification_receipt_sha256",
        "phobert_release_receipt_authority_sha256",
        "phobert_segmenter_authority_sha256",
        "runtime_dependency_authority_sha256",
        "runtime_materialization_receipt_sha256",
    )
}
if any(
    not isinstance(value, str)
    or len(value) != 64
    or any(character not in "0123456789abcdef" for character in value)
    for value in required_phase40_authorities.values()
):
    raise RuntimeError("required Phase 40 authority digest is absent")
normalized_root = os.path.normcase(os.path.abspath(os.path.normpath(clean_root)))
payload = canonical({
    "schema_version": "phase41-execution-materialization-v1",
    "mode": "locked-clean-runtime",
    "preparation_scope": scope,
    "created_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    "source_manifest_sha256": hashlib.sha256(source_bytes).hexdigest(),
    "source_tree_sha256": source["source_tree_sha256"],
    "protocols_sha256": hashlib.sha256(protocol_bytes).hexdigest(),
    "model_bundle_authorities_sha256": hashlib.sha256(bundle_bytes).hexdigest(),
    **required_phase40_authorities,
    "launcher_sha256": source["launcher"]["sha256"],
    "launcher_host_sha256": launcher_host["sha256"],
    "external_launcher_authority_sha256": external_launcher_authority_sha256,
    "python_executable_sha256": source["python"]["sha256"],
    "clean_runtime_root_sha256": hashlib.sha256(normalized_root.encode("utf-8")).hexdigest(),
    "source_file_count": len(source["files"]),
    "source_handles_locked_at_launch": True,
    "launcher_capability_sha256": launcher_capability_sha256,
    "launcher_process_id": launcher_process_id,
    "launcher_process_image_path_sha256": hashlib.sha256(
        normalized_launcher_image.encode("utf-8")
    ).hexdigest(),
    "launcher_process_image_sha256": launcher_process_image_sha256,
    "runtime_import_roots": source["python"]["runtime_import_roots"],
})
flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_BINARY", 0)
descriptor = os.open(receipt_path, flags, 0o600)
try:
    os.write(descriptor, payload)
    os.fsync(descriptor)
finally:
    os.close(descriptor)
'@
    & $PythonPath -I -S -s -B -c $ReceiptBuilder `
        $MaterializationReceipt $SourceManifest $PreparedRequest `
        $ProtocolAuthority $CleanRoot $CapabilitySha256 ([string]$PID) `
        $LauncherImagePath $LauncherImageLock.Sha256
    if ($LASTEXITCODE -ne 0) {
        throw "Pinned Python failed to freeze the execution materialization receipt"
    }
    $ReceiptLock = Open-LockedReadFile -LiteralPath $MaterializationReceipt
    $AuthorityLocks.Add($ReceiptLock.Stream)

    $Bootstrap = @'
import hashlib
import importlib.abc
import importlib.util
import json
import os
import platform
from pathlib import Path
import runpy
import sys

def reject_duplicates(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise RuntimeError(f"duplicate JSON key: {key}")
        result[key] = value
    return result

def canonical(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n").encode("utf-8")

def load(path):
    payload = Path(path).read_bytes()
    value = json.loads(payload.decode("utf-8", errors="strict"), object_pairs_hook=reject_duplicates, parse_constant=lambda value: (_ for _ in ()).throw(RuntimeError(value)))
    if payload != canonical(value):
        raise RuntimeError("authority is not canonical JSON")
    return value, payload

root = Path(sys.argv.pop(1)).absolute()
output = Path(sys.argv.pop(1)).absolute()
source, source_bytes = load(output / "execution-source-manifest.json")
receipt, _ = load(output / "execution-materialization-receipt.json")
request, _ = load(output / "evaluation-request.json")
_, protocol_bytes = load(output / "frozen-inference-protocols.json")
scope = source.get("preparation_scope")
if scope not in {"production_canonical", "synthetic_test"} or request.get("preparation_scope") != scope or receipt.get("preparation_scope") != scope:
    raise RuntimeError("request/source/materialization preparation scope drifted")
launcher_host = source.get("launcher_host")
if not isinstance(launcher_host, dict) or launcher_host.get("mode") != (
    "phase40_external_launcher_authority" if scope == "production_canonical" else "synthetic_test"
):
    raise RuntimeError("launcher host authority mode drifted")
external_launcher_authority_sha256 = (
    launcher_host.get("external_launch_receipt_sha256")
    if scope == "production_canonical"
    else "0" * 64
)
if scope == "production_canonical" and external_launcher_authority_sha256 != request["authorities"].get("comparison_launch_receipt_sha256"):
    raise RuntimeError("external launcher authority differs from prepared request")
if platform.python_version() != source["python"]["version"]:
    raise RuntimeError("pinned Python version drifted")
normalized_root = os.path.normcase(os.path.abspath(os.path.normpath(os.fspath(root))))
expected = {
    "source_manifest_sha256": hashlib.sha256(source_bytes).hexdigest(),
    "source_tree_sha256": source["source_tree_sha256"],
    "protocols_sha256": hashlib.sha256(protocol_bytes).hexdigest(),
    "model_bundle_authorities_sha256": hashlib.sha256(canonical(request["authorities"]["model_bundle_authorities"])).hexdigest(),
    "qwen_gguf_verification_receipt_sha256": request["authorities"]["qwen_gguf_verification_receipt_sha256"],
    "phobert_release_receipt_authority_sha256": request["authorities"]["phobert_release_receipt_authority_sha256"],
    "phobert_segmenter_authority_sha256": request["authorities"]["phobert_segmenter_authority_sha256"],
    "runtime_dependency_authority_sha256": request["authorities"]["runtime_dependency_authority_sha256"],
    "runtime_materialization_receipt_sha256": request["authorities"]["runtime_materialization_receipt_sha256"],
    "launcher_sha256": source["launcher"]["sha256"],
    "launcher_host_sha256": launcher_host["sha256"],
    "external_launcher_authority_sha256": external_launcher_authority_sha256,
    "python_executable_sha256": hashlib.sha256(Path(sys.executable).read_bytes()).hexdigest(),
    "clean_runtime_root_sha256": hashlib.sha256(normalized_root.encode("utf-8")).hexdigest(),
    "source_file_count": len(source["files"]),
    "runtime_import_roots": source["python"]["runtime_import_roots"],
}
if receipt.get("schema_version") != "phase41-execution-materialization-v1" or receipt.get("mode") != "locked-clean-runtime" or receipt.get("source_handles_locked_at_launch") is not True:
    raise RuntimeError("materialization receipt schema/state drifted")
for key, value in expected.items():
    if receipt.get(key) != value:
        raise RuntimeError(f"materialization receipt drifted: {key}")
normalized_launcher_host = os.path.normcase(
    os.path.abspath(os.path.normpath(str(launcher_host["path"])))
)
if receipt.get("launcher_process_id") != os.getppid() or receipt.get(
    "launcher_process_image_path_sha256"
) != hashlib.sha256(normalized_launcher_host.encode("utf-8")).hexdigest() or receipt.get(
    "launcher_process_image_sha256"
) != launcher_host["sha256"]:
    raise RuntimeError("materialization parent differs from launcher host authority")
expected_files = {row["path"]: row for row in source["files"]}
actual_files = {
    path.relative_to(root).as_posix(): path
    for path in root.rglob("*")
    if path.is_file()
}
if set(actual_files) != set(expected_files):
    raise RuntimeError("clean runtime file set drifted before import")
for name, authority in expected_files.items():
    payload = actual_files[name].read_bytes()
    if len(payload) != authority["bytes"] or hashlib.sha256(payload).hexdigest() != authority["sha256"]:
        raise RuntimeError(f"clean runtime source drifted before import: {name}")
    actual_files[name] = payload
runtime_roots = [os.path.abspath(os.path.normpath(value)) for value in expected["runtime_import_roots"]]
if any(not os.path.isdir(value) for value in runtime_roots):
    raise RuntimeError("runtime import root is absent")
bound_sources = {}
bound_packages = set()
for name, payload in actual_files.items():
    if not name.startswith("src/") or not name.endswith(".py"):
        raise RuntimeError(f"clean runtime contains a non-Python project source: {name}")
    parts = name[:-3].split("/")
    if parts[-1] == "__init__":
        parts = parts[:-1]
        is_package = True
    else:
        is_package = False
    if not parts or any(not part.isidentifier() for part in parts):
        raise RuntimeError(f"clean runtime source has an invalid module name: {name}")
    module_name = ".".join(parts)
    if module_name in bound_sources:
        raise RuntimeError(f"clean runtime maps two files to one module: {module_name}")
    bound_sources[module_name] = (payload, name)
    if is_package:
        bound_packages.add(module_name)
if "src" not in bound_packages or "src.model_adaptation.cli" not in bound_sources:
    raise RuntimeError("clean runtime lacks the fixed package/entry module")
if any(name == "src" or name.startswith("src.") for name in sys.modules):
    raise RuntimeError("project source was imported before bound-source installation")

class BoundSourceLoader(importlib.abc.MetaPathFinder, importlib.abc.Loader):
    def find_spec(self, fullname, path=None, target=None):
        del path, target
        if fullname == "src" or fullname.startswith("src."):
            if fullname not in bound_sources:
                raise ModuleNotFoundError(f"unbound project module rejected: {fullname}")
            expected_path = self.get_filename(fullname)
            spec = importlib.util.spec_from_file_location(
                fullname,
                expected_path,
                loader=self,
                submodule_search_locations=(
                    [] if self.is_package(fullname) else None
                ),
            )
            if (
                spec is None
                or spec.has_location is not True
                or spec.origin != expected_path
            ):
                raise RuntimeError("bound project module lacks its exact source location")
            return spec
        return None

    def create_module(self, spec):
        del spec
        return None

    def exec_module(self, module):
        expected_path = self.get_filename(module.__name__)
        spec = getattr(module, "__spec__", None)
        if (
            getattr(module, "__file__", None) != expected_path
            or spec is None
            or spec.has_location is not True
            or spec.origin != expected_path
        ):
            raise RuntimeError("bound project module source location drifted")
        code = self.get_code(module.__name__)
        exec(code, module.__dict__)

    def get_code(self, fullname):
        payload, name = bound_sources[fullname]
        return compile(
            payload,
            f"phase41-bound:{name}",
            "exec",
            dont_inherit=True,
            optimize=0,
        )

    def get_filename(self, fullname):
        return os.fspath(root / bound_sources[fullname][1])

    def get_source(self, fullname):
        return bound_sources[fullname][0].decode("utf-8", errors="strict")

    def is_package(self, fullname):
        return fullname in bound_packages

sys.meta_path.insert(0, BoundSourceLoader())
sys.path[:] = [*runtime_roots, *[value for value in sys.path if value not in {"", str(root), *runtime_roots}]]
sys.argv = ["src.model_adaptation.cli", "phase41-run-once", "--output-root", str(output)]
runpy.run_module("src.model_adaptation.cli", run_name="__main__", alter_sys=True)
'@
    $ChildProcess = $null
    try {
        $StartInfo = [System.Diagnostics.ProcessStartInfo]::new()
        $StartInfo.FileName = $PythonPath
        $StartInfo.UseShellExecute = $false
        $StartInfo.CreateNoWindow = $true
        $StartInfo.RedirectStandardInput = $true
        foreach ($Argument in @(
            '-I', '-S', '-s', '-B', '-c', $Bootstrap,
            $CleanRoot, $ResolvedOutput
        )) {
            [void]$StartInfo.ArgumentList.Add([string]$Argument)
        }
        $ChildProcess = [System.Diagnostics.Process]::Start($StartInfo)
        if ($null -eq $ChildProcess) {
            throw "Pinned Python child process did not start"
        }
        $CapabilityStream = $ChildProcess.StandardInput.BaseStream
        $CapabilityStream.Write($CapabilityBytes, 0, $CapabilityBytes.Length)
        $CapabilityStream.Flush()
        $ChildProcess.WaitForExit()
        if ($ChildProcess.ExitCode -ne 0) {
            throw "Phase 41 isolated run failed with exit code $($ChildProcess.ExitCode)"
        }
    }
    finally {
        if ($null -ne $ChildProcess) { $ChildProcess.Dispose() }
    }
}
finally {
    foreach ($Handle in $CleanLocks) { $Handle.Dispose() }
    foreach ($Handle in $SourceLocks) { $Handle.Dispose() }
    foreach ($Handle in $AuthorityLocks) { $Handle.Dispose() }
    if ($null -eq $OldPythonPath) { Remove-Item Env:PYTHONPATH -ErrorAction SilentlyContinue } else { $env:PYTHONPATH = $OldPythonPath }
    if ($null -eq $OldPythonHome) { Remove-Item Env:PYTHONHOME -ErrorAction SilentlyContinue } else { $env:PYTHONHOME = $OldPythonHome }
    if ($null -eq $OldNoUserSite) { Remove-Item Env:PYTHONNOUSERSITE -ErrorAction SilentlyContinue } else { $env:PYTHONNOUSERSITE = $OldNoUserSite }
}
