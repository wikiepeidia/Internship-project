[CmdletBinding()]
param(
    [string]$RepairScript = ''
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Assert-True {
    param([bool]$Condition, [string]$Message)
    if (-not $Condition) { throw $Message }
}

function Get-LowerSha256 {
    param([Parameter(Mandatory)][string]$Path)
    return (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLowerInvariant()
}

function Write-Utf8 {
    param(
        [Parameter(Mandatory)][string]$Path,
        [Parameter(Mandatory)][AllowEmptyString()][string]$Content
    )
    [System.IO.File]::WriteAllText($Path, $Content, [System.Text.UTF8Encoding]::new($false))
}

function Invoke-ExpectedFailure {
    param([Parameter(Mandatory)][scriptblock]$Action, [Parameter(Mandatory)][string]$Pattern)
    $message = ''
    try { & $Action }
    catch { $message = $_.Exception.Message }
    if ($message -notmatch $Pattern) {
        throw "Expected failure matching '$Pattern', actual='$message'"
    }
}

$repairScript = if ([string]::IsNullOrWhiteSpace($RepairScript)) {
    Join-Path $PSScriptRoot 'seal-phase40-phobert-v12-telemetry-v13.ps1'
}
else {
    [System.IO.Path]::GetFullPath($RepairScript)
}
$tempBase = [System.IO.Path]::GetFullPath([System.IO.Path]::GetTempPath())
$tempRoot = Join-Path $tempBase ("phase40-seal-v13-test-{0}" -f [Guid]::NewGuid().ToString('N'))
[void][System.IO.Directory]::CreateDirectory($tempRoot)

try {
    $controllerPath = Join-Path $tempRoot 'controller-v12.ps1'
    $chainLogPath = Join-Path $tempRoot 'chain-v12.log'
    $telemetryCsvPath = Join-Path $tempRoot 'telemetry-v12.csv'
    $telemetryStderrPath = Join-Path $tempRoot 'telemetry-v12.stderr.log'
    $stopReceiptPath = Join-Path $tempRoot 'telemetry-v12.stop.json'
    $runEvidencePath = Join-Path $tempRoot 'run-evidence.json'
    $requestPath = Join-Path $tempRoot 'request.json'
    $baseManifestPath = Join-Path $tempRoot 'base.provenance.json'
    $leasePath = Join-Path $tempRoot 'controller.lease'
    $summaryPath = Join-Path $tempRoot 'summary-v13.json'
    $verificationPath = Join-Path $tempRoot 'summary-v13.verification.json'

    $controllerPid = 42001
    $controllerCreation = [datetime]::Parse('2026-01-01T00:00:00Z').ToFileTimeUtc()
    $telemetryPid = 42002
    $telemetryCreation = [datetime]::Parse('2026-01-01T00:00:00Z').AddMilliseconds(500).ToFileTimeUtc()
    $trainerPid = 42003
    $wrapperSha256 = 'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa'
    $runId = 'phase40-phobert-full-seed42-v12-fixture'

    Write-Utf8 -Path $controllerPath -Content '# frozen fixture controller'
    Write-Utf8 -Path $requestPath -Content '{"schema_version":"fixture-request-v1"}'
    Write-Utf8 -Path $baseManifestPath -Content '{"schema_version":"fixture-base-v1"}'
    Write-Utf8 -Path $telemetryStderrPath -Content ''
    Write-Utf8 -Path $leasePath -Content ''

    $chain = @(
        "2026-01-01T00:00:02.0000000Z controller_pid=$controllerPid controller_creation_utc_filetime_ticks=$controllerCreation launched Python operation=phobert-train-fresh child_pid=$trainerPid preflight=fixture",
        "2026-01-01T00:00:18.0000000Z controller_pid=$controllerPid controller_creation_utc_filetime_ticks=$controllerCreation phobert-train-fresh exit=0",
        "2026-01-01T00:00:19.0000000Z controller_pid=$controllerPid controller_creation_utc_filetime_ticks=$controllerCreation verify-phobert-run-evidence exit=0",
        "2026-01-01T00:00:20.0000000Z controller_pid=$controllerPid controller_creation_utc_filetime_ticks=$controllerCreation render-phobert-graphs exit=0",
        "2026-01-01T00:00:21.0000000Z controller_pid=$controllerPid controller_creation_utc_filetime_ticks=$controllerCreation verify-phobert-run-evidence exit=0",
        "2026-01-01T00:00:21.1000000Z controller_pid=$controllerPid controller_creation_utc_filetime_ticks=$controllerCreation Qwen evidence/GGUF verified; full local PhoBERT evidence verified.",
        "2026-01-01T00:00:51.1000000Z controller_pid=$controllerPid controller_creation_utc_filetime_ticks=$controllerCreation terminal failure: PhoBERT telemetry controlled-stop failure: PhoBERT telemetry process failed controlled stop within 30 seconds: pid=$telemetryPid",
        "2026-01-01T00:00:51.2000000Z controller_pid=$controllerPid controller_creation_utc_filetime_ticks=$controllerCreation releasing exclusive controller lease path=$leasePath terminal_status=failed"
    ) -join [Environment]::NewLine
    Write-Utf8 -Path $chainLogPath -Content ($chain + [Environment]::NewLine)

    $headers = @(
        'timestamp_utc','elapsed_seconds','started_at_utc','gpu_name','vram_total_mib',
        'vram_used_mib','vram_free_mib','gpu_util_percent','gpu_temp_c','gpu_power_w',
        'python_pid','python_rss_bytes','system_ram_used_bytes','system_ram_available_bytes','d_free_bytes'
    )
    $fixtureRows = @(
        [ordered]@{ timestamp_utc='2026-01-01T00:00:01.5000000Z'; elapsed_seconds='1,000'; started_at_utc='2026-01-01T00:00:00.5000000Z'; gpu_name='Fixture GPU'; vram_total_mib='8000'; vram_used_mib='0'; vram_free_mib='7900'; gpu_util_percent='0'; gpu_temp_c='50'; gpu_power_w='10.5'; python_pid=''; python_rss_bytes='0'; system_ram_used_bytes='1000'; system_ram_available_bytes='2000'; d_free_bytes='3000' },
        [ordered]@{ timestamp_utc='2026-01-01T00:00:11.5000000Z'; elapsed_seconds='11,000'; started_at_utc='2026-01-01T00:00:00.5000000Z'; gpu_name='Fixture GPU'; vram_total_mib='8000'; vram_used_mib='3600'; vram_free_mib='4300'; gpu_util_percent='90'; gpu_temp_c='60'; gpu_power_w='40.5'; python_pid="$trainerPid"; python_rss_bytes='5000'; system_ram_used_bytes='1500'; system_ram_available_bytes='1500'; d_free_bytes='2900' },
        [ordered]@{ timestamp_utc='2026-01-01T00:00:21.5000000Z'; elapsed_seconds='21,000'; started_at_utc='2026-01-01T00:00:00.5000000Z'; gpu_name='Fixture GPU'; vram_total_mib='8000'; vram_used_mib='0'; vram_free_mib='7900'; gpu_util_percent='0'; gpu_temp_c='52'; gpu_power_w='11.5'; python_pid=''; python_rss_bytes='0'; system_ram_used_bytes='1200'; system_ram_available_bytes='1800'; d_free_bytes='2800' },
        [ordered]@{ timestamp_utc='2026-01-01T00:00:31.5000000Z'; elapsed_seconds='31,000'; started_at_utc='2026-01-01T00:00:00.5000000Z'; gpu_name='Fixture GPU'; vram_total_mib='8000'; vram_used_mib='0'; vram_free_mib='7900'; gpu_util_percent='0'; gpu_temp_c='51'; gpu_power_w='10.0'; python_pid=''; python_rss_bytes='0'; system_ram_used_bytes='1100'; system_ram_available_bytes='1900'; d_free_bytes='2700' }
    )
    $csvObjects = foreach ($fixtureRow in $fixtureRows) { [pscustomobject]$fixtureRow }
    $csvText = ($csvObjects | Select-Object $headers | ConvertTo-Csv -NoTypeInformation) -join [Environment]::NewLine
    Write-Utf8 -Path $telemetryCsvPath -Content ($csvText + [Environment]::NewLine)

    $stopPayload = [ordered]@{
        schema_version = 'phase40-telemetry-controlled-stop-v1'
        requested_at_utc = '2026-01-01T00:00:21.2000000Z'
        controller_pid = $controllerPid
        controller_creation_utc_filetime_ticks = $controllerCreation
        telemetry_pid = $telemetryPid
        telemetry_creation_utc_filetime_ticks = $telemetryCreation
        telemetry_wrapper_sha256 = $wrapperSha256
        stop_reason = 'terminal telemetry evidence seal'
    }
    Write-Utf8 -Path $stopReceiptPath -Content (($stopPayload | ConvertTo-Json -Depth 4) + [Environment]::NewLine)

    $runEvidence = [ordered]@{
        schema_version = 'phase40-run-evidence-v1'
        status = 'complete'
        failure_reason = $null
        run_id = $runId
        selected_checkpoint = [ordered]@{ optimizer_step = 100; safety_gate_passed = $true }
        artifacts = @(
            [ordered]@{ role='events'; sha256=('1' * 64) },
            [ordered]@{ role='graph_output'; sha256=('2' * 64) },
            [ordered]@{ role='model_artifact'; sha256=('3' * 64) },
            [ordered]@{ role='metrics'; sha256=('4' * 64) }
        )
    }
    Write-Utf8 -Path $runEvidencePath -Content (($runEvidence | ConvertTo-Json -Depth 8) + [Environment]::NewLine)

    $common = @{
        ControllerPath = $controllerPath
        ChainLogPath = $chainLogPath
        TelemetryCsvPath = $telemetryCsvPath
        TelemetryStderrPath = $telemetryStderrPath
        StopReceiptPath = $stopReceiptPath
        RunEvidencePath = $runEvidencePath
        RequestPath = $requestPath
        BaseManifestPath = $baseManifestPath
        ControllerLeasePath = $leasePath
        SummaryPath = $summaryPath
        VerificationReceiptPath = $verificationPath
        ExpectedControllerSha256 = Get-LowerSha256 $controllerPath
        ExpectedChainLogSha256 = Get-LowerSha256 $chainLogPath
        ExpectedTelemetryCsvSha256 = Get-LowerSha256 $telemetryCsvPath
        ExpectedTelemetryStderrSha256 = Get-LowerSha256 $telemetryStderrPath
        ExpectedStopReceiptSha256 = Get-LowerSha256 $stopReceiptPath
        ExpectedRunEvidenceSha256 = Get-LowerSha256 $runEvidencePath
        ExpectedRequestSha256 = Get-LowerSha256 $requestPath
        ExpectedBaseManifestSha256 = Get-LowerSha256 $baseManifestPath
        ExpectedControllerPid = $controllerPid
        ExpectedControllerCreationUtcFileTimeTicks = $controllerCreation
        ExpectedTelemetryPid = $telemetryPid
        ExpectedTelemetryCreationUtcFileTimeTicks = $telemetryCreation
        ExpectedTrainerPid = $trainerPid
        ExpectedTelemetryWrapperSha256 = $wrapperSha256
        ExpectedRunId = $runId
    }

    $check = & $repairScript @common -CheckOnly | ConvertFrom-Json
    Assert-True ($check.status -eq 'validated') 'check-only did not validate the fixture'
    Assert-True (-not (Test-Path -LiteralPath $summaryPath)) 'check-only wrote the summary'
    Assert-True (-not (Test-Path -LiteralPath $verificationPath)) 'check-only wrote the receipt'

    $sealed = & $repairScript @common | ConvertFrom-Json
    Assert-True ($sealed.status -eq 'sealed') 'repair did not seal'
    Assert-True (Test-Path -LiteralPath $summaryPath -PathType Leaf) 'summary missing'
    Assert-True (Test-Path -LiteralPath $verificationPath -PathType Leaf) 'verification receipt missing'
    $summary = Get-Content -Raw -LiteralPath $summaryPath | ConvertFrom-Json -DateKind String
    $receipt = Get-Content -Raw -LiteralPath $verificationPath | ConvertFrom-Json -DateKind String
    Assert-True ($summary.telemetry_shutdown_status -eq 'forced_after_controller_timeout') 'shutdown truth was not preserved'
    Assert-True ($summary.telemetry_process_exit_code_verified -eq $false) 'repair invented a clean process exit'
    Assert-True ($summary.elapsed_seconds_encoding -eq 'legacy-fixed-comma-decimal') 'legacy decimal encoding not recorded'
    Assert-True ([int]$summary.sample_count -eq 4) 'sample count mismatch'
    Assert-True ([double]$summary.final_sample_after_stop_seconds -gt 0) 'post-stop coverage was not recorded'
    Assert-True ($receipt.telemetry_summary_sha256 -eq (Get-LowerSha256 $summaryPath)) 'summary hash not verified'

    Invoke-ExpectedFailure -Pattern 'non-fresh seal target' -Action { & $repairScript @common | Out-Null }

    $mixedCsvPath = Join-Path $tempRoot 'telemetry-mixed.csv'
    $mixedText = $csvText.Replace('"11,000"', '"11.000"')
    Write-Utf8 -Path $mixedCsvPath -Content ($mixedText + [Environment]::NewLine)
    $mixed = @{} + $common
    $mixed.TelemetryCsvPath = $mixedCsvPath
    $mixed.ExpectedTelemetryCsvSha256 = Get-LowerSha256 $mixedCsvPath
    $mixed.SummaryPath = Join-Path $tempRoot 'mixed-summary.json'
    $mixed.VerificationReceiptPath = Join-Path $tempRoot 'mixed-receipt.json'
    Invoke-ExpectedFailure -Pattern 'legacy comma-decimal' -Action { & $repairScript @mixed -CheckOnly | Out-Null }

    $wrongHash = @{} + $common
    $wrongHash.SummaryPath = Join-Path $tempRoot 'wrong-hash-summary.json'
    $wrongHash.VerificationReceiptPath = Join-Path $tempRoot 'wrong-hash-receipt.json'
    $wrongHash.ExpectedTelemetryCsvSha256 = '0' * 64
    Invoke-ExpectedFailure -Pattern 'SHA-256 mismatch' -Action { & $repairScript @wrongHash -CheckOnly | Out-Null }

    $source = Get-Content -Raw -LiteralPath $repairScript
    Assert-True ($source -notmatch '(?im)\bStart-Process\b|System\.Diagnostics\.Process(?:StartInfo|\.Start)') 'seal-only repair contains a process launch construct'
    Assert-True ($source -notmatch '(?im)^\s*&\s+.*(?:python|phase40-train)') 'seal-only repair invokes a trainer/Python command'
    Assert-True ($source -notmatch '(?i)data[\\/]+splits[\\/]+(?:test|held)|(?:test|held)[-_]?split') 'seal-only repair references a reserved split'

    [pscustomobject]@{
        status = 'passed'
        scenarios = @('check-only','seal','existing-target rejection','mixed-decimal rejection','hash rejection','static no-launch boundary')
        repair_script = $repairScript
    } | ConvertTo-Json -Depth 4
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
