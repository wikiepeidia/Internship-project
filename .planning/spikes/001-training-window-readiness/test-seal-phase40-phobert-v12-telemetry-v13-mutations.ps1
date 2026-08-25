[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$testPath = Join-Path $PSScriptRoot 'test-seal-phase40-phobert-v12-telemetry-v13.ps1'
$sourcePath = Join-Path $PSScriptRoot 'seal-phase40-phobert-v12-telemetry-v13.ps1'
$tempBase = [System.IO.Path]::GetFullPath([System.IO.Path]::GetTempPath())
$tempRoot = Join-Path $tempBase ("phase40-seal-v13-mutants-{0}" -f [Guid]::NewGuid().ToString('N'))
[void][System.IO.Directory]::CreateDirectory($tempRoot)

function Invoke-Mutant {
    param(
        [Parameter(Mandatory)][string]$Name,
        [Parameter(Mandatory)][string]$Source,
        [Parameter(Mandatory)][string]$OldText,
        [Parameter(Mandatory)][string]$NewText
    )
    $mutated = $Source.Replace($OldText, $NewText)
    if ($mutated -eq $Source) { throw "Mutant did not alter source: $Name" }
    $mutantPath = Join-Path $tempRoot ("{0}.ps1" -f $Name)
    [System.IO.File]::WriteAllText($mutantPath, $mutated, [System.Text.UTF8Encoding]::new($false))
    $killed = $false
    $failure = ''
    try { & $testPath -RepairScript $mutantPath | Out-Null }
    catch {
        $killed = $true
        $failure = $_.Exception.Message
    }
    return [pscustomobject]@{ name=$Name; killed=$killed; failure=$failure }
}

try {
    $source = [System.IO.File]::ReadAllText($sourcePath)
    $elapsedMutant = Invoke-Mutant `
        -Name 'elapsed-decoder-mutant' `
        -Source $source `
        -OldText '$Value.Replace('','', ''.'')' `
        -NewText '$Value.Replace('','', '''')'
    $truthMutant = Invoke-Mutant `
        -Name 'clean-exit-truth-mutant' `
        -Source $source `
        -OldText 'telemetry_process_exit_code_verified = $false' `
        -NewText 'telemetry_process_exit_code_verified = $true'
    $results = @($elapsedMutant, $truthMutant)
    $baseline = & $testPath | ConvertFrom-Json
    [pscustomobject]@{
        status = if (@($results | Where-Object { -not $_.killed }).Count -eq 0 -and $baseline.status -eq 'passed') { 'passed' } else { 'failed' }
        mutants = $results
        baseline_status = $baseline.status
    } | ConvertTo-Json -Depth 6
    if (@($results | Where-Object { -not $_.killed }).Count -ne 0 -or $baseline.status -ne 'passed') {
        exit 1
    }
}
finally {
    $resolvedTempRoot = [System.IO.Path]::GetFullPath($tempRoot)
    if (-not $resolvedTempRoot.StartsWith($tempBase, [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "Refusing cleanup outside temp root: $resolvedTempRoot"
    }
    if (Test-Path -LiteralPath $resolvedTempRoot) {
        Remove-Item -LiteralPath $resolvedTempRoot -Recurse -Force
    }
}
