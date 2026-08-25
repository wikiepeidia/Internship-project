[CmdletBinding()]
param(
    [string]$OutputRoot
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
if ([string]::IsNullOrWhiteSpace($OutputRoot)) {
    throw "OutputRoot is required"
}

# This launcher never accepts a split, model, claim-registry, or retry override.
# Python owns the sole CreateFileW handle with FileShare.None after the durable
# machine claim. The launcher's job is to bind the fixed authorities and create
# an isolated interpreter process from the reviewed clean runtime.
$ResolvedOutput = [System.IO.Path]::GetFullPath($OutputRoot)
$ProgramDataRoot = [Environment]::GetFolderPath(
    [Environment+SpecialFolder]::CommonApplicationData
)
if ([string]::IsNullOrWhiteSpace($ProgramDataRoot)) {
    throw "ProgramData identity is unavailable"
}
$ClaimRegistry = Join-Path $ProgramDataRoot "VNPhish\phase41-one-shot-claims"
if (-not [System.IO.Directory]::Exists($ClaimRegistry)) {
    throw "Protected Phase 41 claim registry is not provisioned"
}
$ClaimAttributes = [System.IO.File]::GetAttributes($ClaimRegistry)
if (($ClaimAttributes -band [System.IO.FileAttributes]::ReparsePoint) -ne 0) {
    throw "Protected Phase 41 claim registry cannot be a reparse point"
}

$LauncherPath = $MyInvocation.MyCommand.Path
$LauncherName = "phase41_one_shot_launcher.ps1"
if ([System.IO.Path]::GetFileName($LauncherPath) -cne $LauncherName) {
    throw "Launcher filename drifted"
}
$LauncherSha256 = (Get-FileHash -LiteralPath $LauncherPath -Algorithm SHA256).Hash.ToLowerInvariant()
if ($LauncherSha256 -notmatch '^[0-9a-f]{64}$') {
    throw "Launcher self-hash failed"
}

$SourceManifest = Join-Path $ResolvedOutput "execution-source-manifest.json"
$ProtocolAuthority = Join-Path $ResolvedOutput "frozen-inference-protocols.json"
$Preauthorization = Join-Path $ResolvedOutput "preauthorization-receipt.json"
$CleanRoot = Join-Path $ResolvedOutput "clean-runtime"
foreach ($RequiredPath in @($SourceManifest, $ProtocolAuthority, $Preauthorization)) {
    if (-not [System.IO.File]::Exists($RequiredPath)) {
        throw "Required Phase 41 authority is absent: $RequiredPath"
    }
}
if (-not [System.IO.Directory]::Exists($CleanRoot)) {
    throw "Reviewed clean runtime is absent"
}
$CleanAttributes = [System.IO.File]::GetAttributes($CleanRoot)
if (($CleanAttributes -band [System.IO.FileAttributes]::ReparsePoint) -ne 0) {
    throw "Reviewed clean runtime cannot be a reparse point"
}

$Python = (Get-Command python -ErrorAction Stop).Source
$OldPythonPath = $env:PYTHONPATH
$OldPythonHome = $env:PYTHONHOME
$OldNoUserSite = $env:PYTHONNOUSERSITE
try {
    Remove-Item Env:PYTHONPATH -ErrorAction SilentlyContinue
    Remove-Item Env:PYTHONHOME -ErrorAction SilentlyContinue
    $env:PYTHONNOUSERSITE = "1"
    $Bootstrap = @'
import runpy
import sys
from pathlib import Path
root = Path(sys.argv.pop(1)).resolve(strict=True)
sys.path[:] = [str(root)]
sys.argv = ["src.model_adaptation.cli", "phase41-run-once", "--output-root", sys.argv[1]]
runpy.run_module("src.model_adaptation.cli", run_name="__main__", alter_sys=True)
'@
    $Arguments = @(
        "-I",
        "-S",
        "-B",
        "-c",
        $Bootstrap,
        $CleanRoot,
        $ResolvedOutput
    )
    & $Python @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "Phase 41 isolated run failed with exit code $LASTEXITCODE"
    }
}
finally {
    if ($null -eq $OldPythonPath) { Remove-Item Env:PYTHONPATH -ErrorAction SilentlyContinue } else { $env:PYTHONPATH = $OldPythonPath }
    if ($null -eq $OldPythonHome) { Remove-Item Env:PYTHONHOME -ErrorAction SilentlyContinue } else { $env:PYTHONHOME = $OldPythonHome }
    if ($null -eq $OldNoUserSite) { Remove-Item Env:PYTHONNOUSERSITE -ErrorAction SilentlyContinue } else { $env:PYTHONNOUSERSITE = $OldNoUserSite }
}
