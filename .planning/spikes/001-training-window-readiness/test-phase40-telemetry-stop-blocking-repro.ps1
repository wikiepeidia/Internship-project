[CmdletBinding()]
param(
    [switch]$UsePhase40Sampler
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$tempBase = [System.IO.Path]::GetFullPath([System.IO.Path]::GetTempPath())
$tempRoot = Join-Path $tempBase ("phase40-telemetry-stop-repro-{0}" -f [Guid]::NewGuid().ToString('N'))
[void][System.IO.Directory]::CreateDirectory($tempRoot)

$samplerPath = Join-Path $tempRoot 'sampler.ps1'
$wrapperPath = Join-Path $tempRoot 'wrapper.ps1'
$samplePath = Join-Path $tempRoot 'samples.txt'
$stopPath = Join-Path $tempRoot 'stop.json'
$preStopMarker = Join-Path $tempRoot 'pre-stop.txt'
$postStopMarker = Join-Path $tempRoot 'post-stop.txt'
$stdoutPath = Join-Path $tempRoot 'stdout.log'
$stderrPath = Join-Path $tempRoot 'stderr.log'
$controllerRoot = 'D:\PROJEct\AI MODELS\phase40-full-local-20260825\controller'
$frozenSamplerPath = Join-Path $controllerRoot 'phase40-system-telemetry-v3.ps1'
$phase40SamplePath = Join-Path $controllerRoot ("system-telemetry-stop-repro-{0}.csv" -f [Guid]::NewGuid().ToString('N'))
$child = $null

$sampler = @'
param([Parameter(Mandatory)][string]$OutputPath)
$ErrorActionPreference = 'Stop'
while ($true) {
    [System.IO.File]::AppendAllText(
        $OutputPath,
        [DateTime]::UtcNow.ToString('o') + [Environment]::NewLine,
        [System.Text.UTF8Encoding]::new($false)
    )
    Start-Sleep -Milliseconds 100
}
'@

$wrapper = @'
param(
    [Parameter(Mandatory)][string]$SamplerPath,
    [Parameter(Mandatory)][string]$SamplePath,
    [Parameter(Mandatory)][string]$StopPath,
    [Parameter(Mandatory)][string]$PreStopMarker,
    [Parameter(Mandatory)][string]$PostStopMarker
)
$ErrorActionPreference = 'Stop'
$engine = [System.Management.Automation.PowerShell]::Create()
try {
    [void]$engine.AddCommand($SamplerPath)
    [void]$engine.AddParameter('OutputPath', $SamplePath)
    $async = $engine.BeginInvoke()
    while (-not (Test-Path -LiteralPath $StopPath -PathType Leaf)) {
        if ($async.IsCompleted) { throw 'sampler exited before stop' }
        Start-Sleep -Milliseconds 25
    }
    [System.IO.File]::WriteAllText($PreStopMarker, [DateTime]::UtcNow.ToString('o'))
    $engine.Stop()
    [System.IO.File]::WriteAllText($PostStopMarker, [DateTime]::UtcNow.ToString('o'))
    try { [void]$engine.EndInvoke($async) } catch {
        if ($_.FullyQualifiedErrorId -notmatch 'PipelineStopped' -and
            $_.Exception -isnot [System.Management.Automation.PipelineStoppedException] -and
            $_.Exception.InnerException -isnot [System.Management.Automation.PipelineStoppedException]) {
            throw
        }
    }
}
finally {
    $engine.Dispose()
}
'@

try {
    if ($UsePhase40Sampler) {
        $expectedSha256 = '1bc33f3726b57297a3cc5a69b36831bbd602edac680ba329224b14cf06231c70'
        $actualSha256 = (Get-FileHash -LiteralPath $frozenSamplerPath -Algorithm SHA256).Hash.ToLowerInvariant()
        if ($actualSha256 -ne $expectedSha256) {
            throw "Frozen sampler identity mismatch: $actualSha256"
        }
        [System.IO.File]::Copy($frozenSamplerPath, $samplerPath, $false)
        $samplePath = $phase40SamplePath
    }
    else {
        [System.IO.File]::WriteAllText($samplerPath, $sampler, [System.Text.UTF8Encoding]::new($false))
    }
    [System.IO.File]::WriteAllText($wrapperPath, $wrapper, [System.Text.UTF8Encoding]::new($false))

    $pwshExe = Join-Path $PSHOME 'pwsh.exe'
    $quoted = foreach ($pathValue in @($wrapperPath, $samplerPath, $samplePath, $stopPath, $preStopMarker, $postStopMarker)) {
        '"' + $pathValue.Replace('"', '\"') + '"'
    }
    $argumentString = @(
        '-NoLogo -NoProfile -NonInteractive',
        "-File $($quoted[0])",
        "-SamplerPath $($quoted[1])",
        "-SamplePath $($quoted[2])",
        "-StopPath $($quoted[3])",
        "-PreStopMarker $($quoted[4])",
        "-PostStopMarker $($quoted[5])"
    ) -join ' '
    $child = Start-Process -FilePath $pwshExe -ArgumentList $argumentString `
        -RedirectStandardOutput $stdoutPath -RedirectStandardError $stderrPath -PassThru
    $expectedStartFileTime = $child.StartTime.ToUniversalTime().ToFileTimeUtc()

    $sampleDeadline = [DateTime]::UtcNow.AddSeconds(5)
    while (-not (Test-Path -LiteralPath $samplePath -PathType Leaf)) {
        if ([DateTime]::UtcNow -ge $sampleDeadline) { throw 'sampler did not create a sample' }
        Start-Sleep -Milliseconds 25
    }

    [System.IO.File]::WriteAllText(
        $stopPath,
        '{"schema_version":"phase40-telemetry-controlled-stop-repro-v1"}',
        [System.Text.UTF8Encoding]::new($false)
    )
    $stoppedCleanly = $child.WaitForExit(2000)
    $live = Get-Process -Id $child.Id -ErrorAction SilentlyContinue
    $identityStillMatches = $null -ne $live -and
        $live.StartTime.ToUniversalTime().ToFileTimeUtc() -eq $expectedStartFileTime
    $preStopObserved = Test-Path -LiteralPath $preStopMarker -PathType Leaf
    $postStopObserved = Test-Path -LiteralPath $postStopMarker -PathType Leaf
    $samples = @(Get-Content -LiteralPath $samplePath)

    if (-not $stoppedCleanly -and $identityStillMatches) {
        Stop-Process -Id $child.Id -Force
        [void]$child.WaitForExit(5000)
    }

    [pscustomobject]@{
        sampler_kind = if ($UsePhase40Sampler) { 'phase40-frozen-copy' } else { 'trivial' }
        child_pid = $child.Id
        controlled_stop_completed = $stoppedCleanly
        pre_stop_marker = $preStopObserved
        post_stop_marker = $postStopObserved
        sample_count = $samples.Count
        stderr = if (Test-Path -LiteralPath $stderrPath) { Get-Content -Raw -LiteralPath $stderrPath } else { '' }
    } | ConvertTo-Json -Depth 4

    if ($UsePhase40Sampler -and ($stoppedCleanly -or -not $preStopObserved -or $postStopObserved)) {
        throw 'The isolated wrapper did not reproduce blocking inside synchronous PowerShell.Stop()'
    }
}
finally {
    if ($null -ne $child) {
        $live = Get-Process -Id $child.Id -ErrorAction SilentlyContinue
        if ($null -ne $live -and
            $live.StartTime.ToUniversalTime().ToFileTimeUtc() -eq $child.StartTime.ToUniversalTime().ToFileTimeUtc()) {
            Stop-Process -Id $child.Id -Force
            [void]$child.WaitForExit(5000)
        }
    }
    $resolvedTempRoot = [System.IO.Path]::GetFullPath($tempRoot)
    if (-not $resolvedTempRoot.StartsWith($tempBase, [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "Refusing cleanup outside temp root: $resolvedTempRoot"
    }
    if (Test-Path -LiteralPath $resolvedTempRoot) {
        Remove-Item -LiteralPath $resolvedTempRoot -Recurse -Force
    }
    if ($UsePhase40Sampler -and (Test-Path -LiteralPath $phase40SamplePath -PathType Leaf)) {
        $resolvedPhase40SamplePath = [System.IO.Path]::GetFullPath($phase40SamplePath)
        $resolvedControllerRoot = [System.IO.Path]::GetFullPath($controllerRoot) + [System.IO.Path]::DirectorySeparatorChar
        if (-not $resolvedPhase40SamplePath.StartsWith($resolvedControllerRoot, [System.StringComparison]::OrdinalIgnoreCase) -or
            -not [System.IO.Path]::GetFileName($resolvedPhase40SamplePath).StartsWith('system-telemetry-stop-repro-', [System.StringComparison]::Ordinal)) {
            throw "Refusing diagnostic output cleanup: $resolvedPhase40SamplePath"
        }
        Remove-Item -LiteralPath $resolvedPhase40SamplePath -Force
    }
}
