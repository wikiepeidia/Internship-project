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
$ClaimRegistry = Join-Path $ProgramDataRoot "VNPhish\phase41-one-shot-claims"
Assert-NoReparseDirectoryAncestors -DirectoryPath $ProgramDataRoot
Assert-NonReparseDirectoryChain -Root $ProgramDataRoot -Leaf $ClaimRegistry
Assert-ProtectedRegistryAcl -RegistryPath $ClaimRegistry

$LauncherPath = [System.IO.Path]::GetFullPath($MyInvocation.MyCommand.Path)
if ([System.IO.Path]::GetFileName($LauncherPath) -cne "phase41_one_shot_launcher.ps1") {
    throw "Launcher filename drifted"
}
$RepositoryRoot = [System.IO.Directory]::GetParent(
    [System.IO.Directory]::GetParent($LauncherPath).FullName
).FullName
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
    if ($Manifest.launcher.path -cne "scripts/phase41_one_shot_launcher.ps1" -or
        [long]$Manifest.launcher.bytes -ne $LauncherLock.Bytes -or
        [string]$Manifest.launcher.sha256 -cne $LauncherLock.Sha256) {
        throw "Launcher bytes differ from the execution source authority"
    }
    if ([string]$Request.authorities.protocols_sha256 -cne
        $LockedAuthorities[$ProtocolAuthority].Sha256) {
        throw "Protocol bytes differ from the prepared request"
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

receipt_path, source_path, request_path, protocol_path, clean_root = sys.argv[1:]
source, source_bytes = load(source_path)
request, _ = load(request_path)
_, protocol_bytes = load(protocol_path)
if platform.python_version() != source["python"]["version"]:
    raise RuntimeError("pinned Python version drifted")
bundle_bytes = canonical(request["authorities"]["model_bundle_authorities"])
normalized_root = os.path.normcase(os.path.abspath(os.path.normpath(clean_root)))
payload = canonical({
    "schema_version": "phase41-execution-materialization-v1",
    "mode": "locked-clean-runtime",
    "created_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    "source_manifest_sha256": hashlib.sha256(source_bytes).hexdigest(),
    "source_tree_sha256": source["source_tree_sha256"],
    "protocols_sha256": hashlib.sha256(protocol_bytes).hexdigest(),
    "model_bundle_authorities_sha256": hashlib.sha256(bundle_bytes).hexdigest(),
    "launcher_sha256": source["launcher"]["sha256"],
    "python_executable_sha256": source["python"]["sha256"],
    "clean_runtime_root_sha256": hashlib.sha256(normalized_root.encode("utf-8")).hexdigest(),
    "source_file_count": len(source["files"]),
    "source_handles_locked_at_launch": True,
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
        $ProtocolAuthority $CleanRoot
    if ($LASTEXITCODE -ne 0) {
        throw "Pinned Python failed to freeze the execution materialization receipt"
    }
    $ReceiptLock = Open-LockedReadFile -LiteralPath $MaterializationReceipt
    $AuthorityLocks.Add($ReceiptLock.Stream)

    $Bootstrap = @'
import hashlib
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
if platform.python_version() != source["python"]["version"]:
    raise RuntimeError("pinned Python version drifted")
normalized_root = os.path.normcase(os.path.abspath(os.path.normpath(os.fspath(root))))
expected = {
    "source_manifest_sha256": hashlib.sha256(source_bytes).hexdigest(),
    "source_tree_sha256": source["source_tree_sha256"],
    "protocols_sha256": hashlib.sha256(protocol_bytes).hexdigest(),
    "model_bundle_authorities_sha256": hashlib.sha256(canonical(request["authorities"]["model_bundle_authorities"])).hexdigest(),
    "launcher_sha256": source["launcher"]["sha256"],
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
runtime_roots = [os.path.abspath(os.path.normpath(value)) for value in expected["runtime_import_roots"]]
if any(not os.path.isdir(value) for value in runtime_roots):
    raise RuntimeError("runtime import root is absent")
sys.path[:] = [str(root), *runtime_roots, *[value for value in sys.path if value not in {"", str(root), *runtime_roots}]]
sys.argv = ["src.model_adaptation.cli", "phase41-run-once", "--output-root", str(output)]
runpy.run_module("src.model_adaptation.cli", run_name="__main__", alter_sys=True)
'@
    & $PythonPath -I -S -s -B -c $Bootstrap $CleanRoot $ResolvedOutput
    if ($LASTEXITCODE -ne 0) {
        throw "Phase 41 isolated run failed with exit code $LASTEXITCODE"
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
