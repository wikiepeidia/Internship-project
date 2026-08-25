Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$controllerSource = Join-Path $PSScriptRoot 'phase40-qwen-to-phobert-chain-v9.ps1'
$testRoot = Join-Path ([System.IO.Path]::GetTempPath()) (
    'phase40-controller-v9-' + [Guid]::NewGuid().ToString('N')
)
$module = $null
$leaseStream = $null

function Assert-True {
    param(
        [Parameter(Mandatory)][bool]$Condition,
        [Parameter(Mandatory)][string]$Message
    )
    if (-not $Condition) {
        throw $Message
    }
}

function Assert-ThrowsLike {
    param(
        [Parameter(Mandatory)][scriptblock]$Action,
        [Parameter(Mandatory)][string]$Pattern,
        [Parameter(Mandatory)][string]$Message
    )
    $didThrow = $false
    $actualMessage = ''
    try {
        $null = & $Action
    }
    catch {
        $didThrow = $true
        $actualMessage = $_.Exception.Message
    }
    if (-not $didThrow) {
        throw "$Message (no exception)"
    }
    if ($actualMessage -notlike $Pattern) {
        throw "$Message (unexpected exception: $actualMessage)"
    }
}

function Get-LowerFileSha256 {
    param([Parameter(Mandatory)][string]$Path)
    return (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLowerInvariant()
}

function New-TelemetryRow {
    param(
        [Parameter(Mandatory)][DateTimeOffset]$Timestamp,
        [Parameter(Mandatory)][double]$ElapsedSeconds,
        [Parameter(Mandatory)][DateTimeOffset]$StartedAt,
        [AllowEmptyString()][string]$PythonPid = ''
    )
    return [pscustomobject][ordered]@{
        timestamp_utc = $Timestamp.ToString('o')
        elapsed_seconds = $ElapsedSeconds.ToString(
            [System.Globalization.CultureInfo]::InvariantCulture
        )
        started_at_utc = $StartedAt.ToString('o')
        gpu_name = 'Synthetic GPU'
        vram_total_mib = '8192'
        vram_used_mib = '1024'
        vram_free_mib = '7168'
        gpu_util_percent = '50'
        gpu_temp_c = '55'
        gpu_power_w = '75'
        python_pid = $PythonPid
        python_rss_bytes = '1048576'
        system_ram_used_bytes = '8589934592'
        system_ram_available_bytes = '25769803776'
        d_free_bytes = '107374182400'
    }
}

function Invoke-TelemetryFixture {
    param(
        [Parameter(Mandatory)][string]$Name,
        [Parameter(Mandatory)][object[]]$Rows,
        [Parameter(Mandatory)][DateTimeOffset]$ProcessStartedAt,
        [Parameter(Mandatory)][DateTimeOffset]$StopRequestedAt,
        [ValidateSet('complete', 'failed')][string]$Status = 'complete',
        [int]$TelemetryExitCode = 0
    )
    $caseRoot = Join-Path $testRoot $Name
    [void](New-Item -ItemType Directory -Path $caseRoot)
    $paths = [ordered]@{
        telemetryPath = Join-Path $caseRoot 'telemetry.csv'
        summaryPath = Join-Path $caseRoot 'summary.json'
        telemetryVerificationReceiptPath = Join-Path $caseRoot 'verification.json'
    }
    foreach ($entry in $paths.GetEnumerator()) {
        Set-SyntheticVariable -Name $entry.Key -Value $entry.Value
    }
    $csv = @($Rows | ConvertTo-Csv -NoTypeInformation)
    [System.IO.File]::WriteAllLines(
        $paths.telemetryPath,
        [string[]]$csv,
        [System.Text.UTF8Encoding]::new($false)
    )
    $receipt = [pscustomobject]@{
        telemetry_pid = 9876
        telemetry_creation_utc_filetime_ticks = $ProcessStartedAt.UtcDateTime.ToFileTimeUtc()
        telemetry_exit_code = $TelemetryExitCode
        telemetry_wrapper_sha256 = ('a' * 64)
        telemetry_stderr_bytes = 0
        telemetry_stderr_sha256 = ('b' * 64)
        telemetry_stop_receipt_sha256 = ('c' * 64)
        telemetry_stop_requested_at_utc = $StopRequestedAt.ToString('o')
    }
    $result = Invoke-SyntheticTelemetrySeal `
        -Status $Status `
        -Detail 'synthetic CPU-only fixture' `
        -StopReceipt $receipt
    return [pscustomobject]@{
        Result = $result
        Paths = [pscustomobject]$paths
    }
}

try {
    if (-not $IsWindows) {
        throw 'The Phase 40 FileShare.None lease test requires Windows'
    }
    [void](New-Item -ItemType Directory -Path $testRoot)

    $parseTokens = $null
    $parseErrors = $null
    $controllerAst = [System.Management.Automation.Language.Parser]::ParseFile(
        $controllerSource,
        [ref]$parseTokens,
        [ref]$parseErrors
    )
    Assert-True ($parseErrors.Count -eq 0) 'v9 controller source does not parse'
    $functionNames = @(
        'Get-LowerSha256',
        'Write-ChainLog',
        'Assert-ControllerLeaseHeld',
        'Open-ControllerLease',
        'Write-PhoBertTelemetrySeal'
    )
    $functionTexts = [System.Collections.Generic.List[string]]::new()
    foreach ($functionName in $functionNames) {
        $matches = @($controllerAst.FindAll({
            param($node)
            $node -is [System.Management.Automation.Language.FunctionDefinitionAst] -and
                $node.Name -eq $functionName
        }, $true))
        Assert-True ($matches.Count -eq 1) "expected exactly one $functionName function"
        $functionTexts.Add($matches[0].Extent.Text)
    }

    # Only selected function definitions are loaded. None of the controller's
    # top-level D-drive, process, model, or dataset operations can execute.
    $modulePath = Join-Path $testRoot 'synthetic-controller-functions.psm1'
    $moduleWrappers = @'
function Initialize-SyntheticContext {
    param([Parameter(Mandatory)][hashtable]$Context)
    foreach ($entry in $Context.GetEnumerator()) {
        Set-Variable -Scope Script -Name $entry.Key -Value $entry.Value
    }
    $script:controllerSha256 = Get-LowerSha256 -Path $PSCommandPath
}

function Set-SyntheticVariable {
    param(
        [Parameter(Mandatory)][string]$Name,
        [Parameter(Mandatory)]$Value
    )
    Set-Variable -Scope Script -Name $Name -Value $Value
}

function Get-SyntheticControllerSha256 {
    return $script:controllerSha256
}

function Acquire-SyntheticLease {
    $script:controllerLeaseStream = Open-ControllerLease
    return $script:controllerLeaseStream
}

function Assert-SyntheticLease {
    Assert-ControllerLeaseHeld
}

function Dispose-SyntheticLease {
    if ($null -ne $script:controllerLeaseStream) {
        $script:controllerLeaseStream.Dispose()
    }
}

function Invoke-SyntheticTelemetrySeal {
    param(
        [Parameter(Mandatory)][string]$Status,
        [string]$Detail = '',
        [Parameter(Mandatory)]$StopReceipt
    )
    return Write-PhoBertTelemetrySeal `
        -Status $Status `
        -Detail $Detail `
        -StopReceipt $StopReceipt
}

Export-ModuleMember -Function @(
    'Initialize-SyntheticContext',
    'Set-SyntheticVariable',
    'Get-SyntheticControllerSha256',
    'Acquire-SyntheticLease',
    'Assert-SyntheticLease',
    'Dispose-SyntheticLease',
    'Invoke-SyntheticTelemetrySeal'
)
'@
    $moduleText = (($functionTexts.ToArray() -join "`n`n") + "`n`n" + $moduleWrappers)
    [System.IO.File]::WriteAllText(
        $modulePath,
        $moduleText,
        [System.Text.UTF8Encoding]::new($false)
    )
    $module = Import-Module -Name $modulePath -Force -PassThru -DisableNameChecking

    $controllerRoot = Join-Path $testRoot 'controller'
    $runRoot = Join-Path $testRoot 'run'
    [void](New-Item -ItemType Directory -Path $controllerRoot)
    [void](New-Item -ItemType Directory -Path $runRoot)
    $requestPath = Join-Path $testRoot 'request.json'
    $baseManifestPath = Join-Path $testRoot 'base-manifest.json'
    [System.IO.File]::WriteAllText(
        $requestPath,
        "{`"synthetic`":true}`n",
        [System.Text.UTF8Encoding]::new($false)
    )
    [System.IO.File]::WriteAllText(
        $baseManifestPath,
        "{`"synthetic`":true}`n",
        [System.Text.UTF8Encoding]::new($false)
    )
    $controllerLeasePath = Join-Path $controllerRoot 'controller.lease'
    $context = @{
        controllerLeasePath = $controllerLeasePath
        controllerLeaseMeaning = 'Synthetic exclusive lease test.'
        controllerLeaseStream = $null
        controllerPid = 4242
        controllerCreationUtc = [DateTime]::Parse(
            '2026-08-25T12:00:00Z',
            [System.Globalization.CultureInfo]::InvariantCulture,
            [System.Globalization.DateTimeStyles]::AdjustToUniversal
        )
        controllerCreationUtcFileTimeTicks = 134321328000000000L
        chainLog = Join-Path $controllerRoot 'chain.log'
        runRoot = $runRoot
        requestPath = $requestPath
        baseManifestPath = $baseManifestPath
        telemetryStartedAtToleranceSeconds = 10
        telemetryFirstSampleToleranceSeconds = 30
        telemetryMaxAdjacentGapSeconds = 30
        telemetryElapsedToleranceSeconds = 5
        telemetryClockSkewToleranceSeconds = 5
        telemetryPath = Join-Path $testRoot 'unset-telemetry.csv'
        summaryPath = Join-Path $testRoot 'unset-summary.json'
        telemetryVerificationReceiptPath = Join-Path $testRoot 'unset-verification.json'
    }
    Initialize-SyntheticContext -Context $context

    $leaseStream = Acquire-SyntheticLease
    Assert-SyntheticLease
    Assert-True ($leaseStream.CanRead -and $leaseStream.CanWrite) `
        'exclusive lease stream is not readable and writable'
    $blockedError = 0
    $secondStream = $null
    try {
        $secondStream = [System.IO.FileStream]::new(
            $controllerLeasePath,
            [System.IO.FileMode]::Open,
            [System.IO.FileAccess]::ReadWrite,
            [System.IO.FileShare]::ReadWrite
        )
    }
    catch [System.IO.IOException] {
        $blockedError = $_.Exception.HResult -band 0xffff
    }
    finally {
        if ($null -ne $secondStream) {
            $secondStream.Dispose()
        }
    }
    Assert-True ($blockedError -eq 32) `
        "second lease open was not blocked by ERROR_SHARING_VIOLATION: $blockedError"
    Dispose-SyntheticLease
    $leaseStream = $null
    Assert-ThrowsLike {
        Assert-SyntheticLease
    } '*exclusive Phase 40 controller lease is not held*' `
        'disposed controller lease still passed its assertion'
    $leasePayload = Get-Content -LiteralPath $controllerLeasePath -Raw -Encoding utf8 |
        ConvertFrom-Json
    Assert-True ($leasePayload.schema_version -eq 'phase40-controller-exclusive-lease-v1') `
        'lease payload schema mismatch'
    Assert-True ($leasePayload.controller_lease_file_share -eq 'none') `
        'lease payload does not record FileShare.None'
    Assert-True ($leasePayload.controller_sha256 -eq (Get-SyntheticControllerSha256)) `
        'lease payload is not bound to the extracted-function module'
    $releasedProbe = [System.IO.FileStream]::new(
        $controllerLeasePath,
        [System.IO.FileMode]::Open,
        [System.IO.FileAccess]::Read,
        [System.IO.FileShare]::ReadWrite
    )
    $releasedProbe.Dispose()

    # Reacquire the same exact lease implementation because Write-ChainLog is
    # deliberately fail-closed on the held lease during telemetry sealing.
    $leaseStream = Acquire-SyntheticLease
    $processStartedAt = [DateTimeOffset]::Parse(
        '2026-08-25T12:00:00Z',
        [System.Globalization.CultureInfo]::InvariantCulture
    )
    $samplerStartedAt = $processStartedAt.AddSeconds(1)
    $validRows = @(
        New-TelemetryRow `
            -Timestamp $processStartedAt.AddSeconds(2) `
            -ElapsedSeconds 1 `
            -StartedAt $samplerStartedAt `
            -PythonPid '4321'
        New-TelemetryRow `
            -Timestamp $processStartedAt.AddSeconds(12) `
            -ElapsedSeconds 11 `
            -StartedAt $samplerStartedAt
    )
    $valid = Invoke-TelemetryFixture `
        -Name 'valid' `
        -Rows $validRows `
        -ProcessStartedAt $processStartedAt `
        -StopRequestedAt $processStartedAt.AddSeconds(15)
    Assert-True ($valid.Result.Status -eq 'complete') 'valid telemetry did not seal complete'
    Assert-True ($valid.Result.SampleCount -eq 2) 'valid telemetry sample count mismatch'
    $summary = Get-Content -LiteralPath $valid.Paths.summaryPath -Raw -Encoding utf8 |
        ConvertFrom-Json
    $verification = Get-Content `
        -LiteralPath $valid.Paths.telemetryVerificationReceiptPath `
        -Raw `
        -Encoding utf8 | ConvertFrom-Json
    Assert-True ($summary.continuous_coverage_verified -eq $true) `
        'valid summary did not record continuous coverage'
    Assert-True ($summary.python_pid_nonempty_sample_count -eq 1) `
        'valid summary Python PID count mismatch'
    Assert-True (@($summary.observed_python_pids).Count -eq 1 -and
        [long]$summary.observed_python_pids[0] -eq 4321) `
        'valid summary Python PID identity mismatch'
    Assert-True ([double]$summary.maximum_observed_adjacent_gap_seconds -eq 10) `
        'valid summary adjacent gap mismatch'
    Assert-True ([double]$summary.maximum_observed_elapsed_delta_seconds -eq 0) `
        'valid summary elapsed delta mismatch'
    Assert-True ($valid.Result.SummarySha256 -eq (Get-LowerFileSha256 $valid.Paths.summaryPath)) `
        'returned summary hash mismatch'
    Assert-True ($verification.telemetry_summary_sha256 -eq $valid.Result.SummarySha256) `
        'verification receipt does not bind the summary hash'
    Assert-True ($valid.Result.VerificationReceiptSha256 -eq
        (Get-LowerFileSha256 $valid.Paths.telemetryVerificationReceiptPath)) `
        'returned verification receipt hash mismatch'

    $emptyPidRows = @(
        New-TelemetryRow -Timestamp $processStartedAt.AddSeconds(2) -ElapsedSeconds 1 -StartedAt $samplerStartedAt
        New-TelemetryRow -Timestamp $processStartedAt.AddSeconds(12) -ElapsedSeconds 11 -StartedAt $samplerStartedAt
    )
    Assert-ThrowsLike {
        Invoke-TelemetryFixture -Name 'empty-pid' -Rows $emptyPidRows `
            -ProcessStartedAt $processStartedAt -StopRequestedAt $processStartedAt.AddSeconds(15)
    } '*no sample with an observed Python PID*' 'empty Python PID evidence passed complete status'

    $zeroPidRows = @(
        New-TelemetryRow -Timestamp $processStartedAt.AddSeconds(2) -ElapsedSeconds 1 -StartedAt $samplerStartedAt -PythonPid '0'
        New-TelemetryRow -Timestamp $processStartedAt.AddSeconds(12) -ElapsedSeconds 11 -StartedAt $samplerStartedAt
    )
    Assert-ThrowsLike {
        Invoke-TelemetryFixture -Name 'zero-pid' -Rows $zeroPidRows `
            -ProcessStartedAt $processStartedAt -StopRequestedAt $processStartedAt.AddSeconds(15)
    } '*invalid python_pid value*' 'PID zero passed as an observed Python process'

    $gapRows = @(
        New-TelemetryRow -Timestamp $processStartedAt.AddSeconds(2) -ElapsedSeconds 1 -StartedAt $samplerStartedAt -PythonPid '4321'
        New-TelemetryRow -Timestamp $processStartedAt.AddSeconds(33) -ElapsedSeconds 32 -StartedAt $samplerStartedAt
    )
    Assert-ThrowsLike {
        Invoke-TelemetryFixture -Name 'gap' -Rows $gapRows `
            -ProcessStartedAt $processStartedAt -StopRequestedAt $processStartedAt.AddSeconds(35)
    } '*sampling gap exceeded limit*' '31-second telemetry gap passed'

    $elapsedRows = @(
        New-TelemetryRow -Timestamp $processStartedAt.AddSeconds(2) -ElapsedSeconds 1 -StartedAt $samplerStartedAt -PythonPid '4321'
        New-TelemetryRow -Timestamp $processStartedAt.AddSeconds(12) -ElapsedSeconds 20 -StartedAt $samplerStartedAt
    )
    Assert-ThrowsLike {
        Invoke-TelemetryFixture -Name 'elapsed' -Rows $elapsedRows `
            -ProcessStartedAt $processStartedAt -StopRequestedAt $processStartedAt.AddSeconds(15)
    } '*elapsed_seconds differs from timestamp-started_at*' 'elapsed-clock drift passed'

    $lateSampler = $processStartedAt.AddSeconds(11)
    $lateStartRows = @(
        New-TelemetryRow -Timestamp $processStartedAt.AddSeconds(12) -ElapsedSeconds 1 -StartedAt $lateSampler -PythonPid '4321'
        New-TelemetryRow -Timestamp $processStartedAt.AddSeconds(22) -ElapsedSeconds 11 -StartedAt $lateSampler
    )
    Assert-ThrowsLike {
        Invoke-TelemetryFixture -Name 'late-sampler' -Rows $lateStartRows `
            -ProcessStartedAt $processStartedAt -StopRequestedAt $processStartedAt.AddSeconds(25)
    } '*started_at is not bound to wrapper creation*' 'late sampler start passed'

    Assert-ThrowsLike {
        Invoke-TelemetryFixture -Name 'stale-final' -Rows $validRows `
            -ProcessStartedAt $processStartedAt -StopRequestedAt $processStartedAt.AddSeconds(43)
    } '*final sample is stale or postdates stop*' '31-second stale final sample passed'

    Assert-ThrowsLike {
        Invoke-TelemetryFixture -Name 'nonzero-exit' -Rows $validRows `
            -ProcessStartedAt $processStartedAt -StopRequestedAt $processStartedAt.AddSeconds(15) `
            -TelemetryExitCode 1
    } '*summary readback identity mismatch*' 'nonzero telemetry exit passed terminal seal'

    Write-Output 'PASS phase40 controller v9 synthetic CPU-only scenarios=9'
}
finally {
    if ($null -ne $leaseStream) {
        try {
            Dispose-SyntheticLease
        }
        catch {
            # Preserve the original test failure while still attempting cleanup.
        }
    }
    if ($null -ne $module) {
        Remove-Module -ModuleInfo $module -Force -ErrorAction SilentlyContinue
    }
    if (Test-Path -LiteralPath $testRoot) {
        $resolvedTestRoot = [System.IO.Path]::GetFullPath($testRoot)
        $resolvedTemp = [System.IO.Path]::GetFullPath(
            [System.IO.Path]::GetTempPath()
        ).TrimEnd([System.IO.Path]::DirectorySeparatorChar) +
            [System.IO.Path]::DirectorySeparatorChar
        if (-not $resolvedTestRoot.StartsWith(
            $resolvedTemp,
            [System.StringComparison]::OrdinalIgnoreCase
        )) {
            throw "Refusing unsafe test cleanup target: $resolvedTestRoot"
        }
        Remove-Item -LiteralPath $resolvedTestRoot -Recurse -Force
    }
}
