[CmdletBinding()]
param(
    [Parameter(Mandatory)][string]$ControllerPath,
    [Parameter(Mandatory)][string]$ChainLogPath,
    [Parameter(Mandatory)][string]$TelemetryCsvPath,
    [Parameter(Mandatory)][string]$TelemetryStderrPath,
    [Parameter(Mandatory)][string]$StopReceiptPath,
    [Parameter(Mandatory)][string]$RunEvidencePath,
    [Parameter(Mandatory)][string]$RequestPath,
    [Parameter(Mandatory)][string]$BaseManifestPath,
    [Parameter(Mandatory)][string]$ControllerLeasePath,
    [Parameter(Mandatory)][string]$SummaryPath,
    [Parameter(Mandatory)][string]$VerificationReceiptPath,
    [Parameter(Mandatory)][ValidatePattern('^[0-9a-f]{64}$')][string]$ExpectedControllerSha256,
    [Parameter(Mandatory)][ValidatePattern('^[0-9a-f]{64}$')][string]$ExpectedChainLogSha256,
    [Parameter(Mandatory)][ValidatePattern('^[0-9a-f]{64}$')][string]$ExpectedTelemetryCsvSha256,
    [Parameter(Mandatory)][ValidatePattern('^[0-9a-f]{64}$')][string]$ExpectedTelemetryStderrSha256,
    [Parameter(Mandatory)][ValidatePattern('^[0-9a-f]{64}$')][string]$ExpectedStopReceiptSha256,
    [Parameter(Mandatory)][ValidatePattern('^[0-9a-f]{64}$')][string]$ExpectedRunEvidenceSha256,
    [Parameter(Mandatory)][ValidatePattern('^[0-9a-f]{64}$')][string]$ExpectedRequestSha256,
    [Parameter(Mandatory)][ValidatePattern('^[0-9a-f]{64}$')][string]$ExpectedBaseManifestSha256,
    [Parameter(Mandatory)][ValidateRange(1, [int]::MaxValue)][int]$ExpectedControllerPid,
    [Parameter(Mandatory)][ValidateRange(1, [long]::MaxValue)][long]$ExpectedControllerCreationUtcFileTimeTicks,
    [Parameter(Mandatory)][ValidateRange(1, [int]::MaxValue)][int]$ExpectedTelemetryPid,
    [Parameter(Mandatory)][ValidateRange(1, [long]::MaxValue)][long]$ExpectedTelemetryCreationUtcFileTimeTicks,
    [Parameter(Mandatory)][ValidateRange(1, [int]::MaxValue)][int]$ExpectedTrainerPid,
    [Parameter(Mandatory)][ValidatePattern('^[0-9a-f]{64}$')][string]$ExpectedTelemetryWrapperSha256,
    [Parameter(Mandatory)][ValidateNotNullOrEmpty()][string]$ExpectedRunId,
    [switch]$CheckOnly
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$expectedHeaders = @(
    'timestamp_utc',
    'elapsed_seconds',
    'started_at_utc',
    'gpu_name',
    'vram_total_mib',
    'vram_used_mib',
    'vram_free_mib',
    'gpu_util_percent',
    'gpu_temp_c',
    'gpu_power_w',
    'python_pid',
    'python_rss_bytes',
    'system_ram_used_bytes',
    'system_ram_available_bytes',
    'd_free_bytes'
)
$numericFields = @(
    'vram_total_mib',
    'vram_used_mib',
    'vram_free_mib',
    'gpu_util_percent',
    'gpu_temp_c',
    'gpu_power_w',
    'python_rss_bytes',
    'system_ram_used_bytes',
    'system_ram_available_bytes',
    'd_free_bytes'
)
$maximumAdjacentGapSeconds = 30.0
$elapsedToleranceSeconds = 5.0
$startupToleranceSeconds = 30.0
$stopTimeoutMinimumSeconds = 29.0
$stopTimeoutMaximumSeconds = 31.5

function Get-FullPath {
    param([Parameter(Mandatory)][string]$Path)
    return [System.IO.Path]::GetFullPath($Path)
}

function Get-LowerSha256 {
    param([Parameter(Mandatory)][string]$Path)
    return (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLowerInvariant()
}

function Assert-FileHash {
    param(
        [Parameter(Mandatory)][string]$Name,
        [Parameter(Mandatory)][string]$Path,
        [Parameter(Mandatory)][string]$ExpectedSha256
    )
    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) {
        throw "$Name is missing: $Path"
    }
    $actual = Get-LowerSha256 -Path $Path
    if ($actual -ne $ExpectedSha256) {
        throw "$Name SHA-256 mismatch: expected=$ExpectedSha256 actual=$actual path=$Path"
    }
}

function ConvertTo-UtcTimestamp {
    param([Parameter(Mandatory)][string]$Value, [Parameter(Mandatory)][string]$Context)
    $parsed = [DateTimeOffset]::MinValue
    if (-not [DateTimeOffset]::TryParseExact(
        $Value,
        'o',
        [System.Globalization.CultureInfo]::InvariantCulture,
        [System.Globalization.DateTimeStyles]::AssumeUniversal -bor [System.Globalization.DateTimeStyles]::AdjustToUniversal,
        [ref]$parsed
    )) {
        throw "Invalid UTC timestamp for ${Context}: $Value"
    }
    return $parsed
}

function ConvertFrom-InvariantNonnegativeNumber {
    param([Parameter(Mandatory)][string]$Value, [Parameter(Mandatory)][string]$Context)
    $number = 0.0
    if (-not [double]::TryParse(
        $Value,
        [System.Globalization.NumberStyles]::Float,
        [System.Globalization.CultureInfo]::InvariantCulture,
        [ref]$number
    ) -or $number -lt 0 -or [double]::IsNaN($number) -or [double]::IsInfinity($number)) {
        throw "Invalid invariant nonnegative number for ${Context}: $Value"
    }
    return $number
}

function ConvertFrom-LegacyElapsedNumber {
    param([Parameter(Mandatory)][string]$Value, [Parameter(Mandatory)][int]$RowIndex)
    if ($Value -notmatch '^[0-9]+,[0-9]{1,3}$') {
        throw "Telemetry row $RowIndex elapsed_seconds is not legacy comma-decimal: $Value"
    }
    return ConvertFrom-InvariantNonnegativeNumber -Value $Value.Replace(',', '.') -Context "row $RowIndex elapsed_seconds"
}

function Write-NewJson {
    param([Parameter(Mandatory)][string]$Path, [Parameter(Mandatory)]$Payload)
    $json = ($Payload | ConvertTo-Json -Depth 12) + [Environment]::NewLine
    $bytes = [System.Text.UTF8Encoding]::new($false).GetBytes($json)
    $stream = [System.IO.FileStream]::new(
        $Path,
        [System.IO.FileMode]::CreateNew,
        [System.IO.FileAccess]::Write,
        [System.IO.FileShare]::Read,
        4096,
        [System.IO.FileOptions]::WriteThrough
    )
    try {
        $stream.Write($bytes, 0, $bytes.Length)
        $stream.Flush($true)
    }
    finally {
        $stream.Dispose()
    }
}

$ControllerPath = Get-FullPath $ControllerPath
$ChainLogPath = Get-FullPath $ChainLogPath
$TelemetryCsvPath = Get-FullPath $TelemetryCsvPath
$TelemetryStderrPath = Get-FullPath $TelemetryStderrPath
$StopReceiptPath = Get-FullPath $StopReceiptPath
$RunEvidencePath = Get-FullPath $RunEvidencePath
$RequestPath = Get-FullPath $RequestPath
$BaseManifestPath = Get-FullPath $BaseManifestPath
$ControllerLeasePath = Get-FullPath $ControllerLeasePath
$SummaryPath = Get-FullPath $SummaryPath
$VerificationReceiptPath = Get-FullPath $VerificationReceiptPath

if ($SummaryPath -eq $VerificationReceiptPath) {
    throw 'Summary and verification receipt paths must be distinct'
}
$inputPaths = @(
    $ControllerPath,
    $ChainLogPath,
    $TelemetryCsvPath,
    $TelemetryStderrPath,
    $StopReceiptPath,
    $RunEvidencePath,
    $RequestPath,
    $BaseManifestPath,
    $ControllerLeasePath
)
foreach ($sealTarget in @($SummaryPath, $VerificationReceiptPath)) {
    if ($inputPaths -contains $sealTarget -or (Test-Path -LiteralPath $sealTarget)) {
        throw "Refusing non-fresh seal target: $sealTarget"
    }
    $parent = Split-Path -Parent $sealTarget
    if (-not (Test-Path -LiteralPath $parent -PathType Container)) {
        throw "Seal target parent is missing: $parent"
    }
}

$hashBindings = @(
    @('controller', $ControllerPath, $ExpectedControllerSha256),
    @('chain log', $ChainLogPath, $ExpectedChainLogSha256),
    @('telemetry CSV', $TelemetryCsvPath, $ExpectedTelemetryCsvSha256),
    @('telemetry stderr', $TelemetryStderrPath, $ExpectedTelemetryStderrSha256),
    @('stop receipt', $StopReceiptPath, $ExpectedStopReceiptSha256),
    @('run evidence', $RunEvidencePath, $ExpectedRunEvidenceSha256),
    @('request', $RequestPath, $ExpectedRequestSha256),
    @('base manifest', $BaseManifestPath, $ExpectedBaseManifestSha256)
)
foreach ($binding in $hashBindings) {
    Assert-FileHash -Name $binding[0] -Path $binding[1] -ExpectedSha256 $binding[2]
}
if ((Get-Item -LiteralPath $TelemetryStderrPath).Length -ne 0) {
    throw 'Telemetry stderr is nonempty; seal-only recovery is not permitted'
}

foreach ($expectedAbsentPid in @($ExpectedControllerPid, $ExpectedTelemetryPid, $ExpectedTrainerPid)) {
    if ($null -ne (Get-Process -Id $expectedAbsentPid -ErrorAction SilentlyContinue)) {
        throw "Expected terminal PID is still live: $expectedAbsentPid"
    }
}
$controllerLeaf = [System.IO.Path]::GetFileName($ControllerPath)
$related = @(
    Get-CimInstance Win32_Process -ErrorAction Stop |
        Where-Object {
            $_.ProcessId -ne $PID -and $_.CommandLine -and (
                $_.CommandLine.Contains($controllerLeaf, [System.StringComparison]::OrdinalIgnoreCase) -or
                ($_.Name -eq 'python.exe' -and $_.CommandLine.Contains($ExpectedRunId, [System.StringComparison]::Ordinal))
            )
        }
)
if ($related.Count -ne 0) {
    throw "Related controller/trainer process is live: pids=$(@($related.ProcessId) -join ',')"
}
if (-not (Test-Path -LiteralPath $ControllerLeasePath -PathType Leaf)) {
    throw "Controller lease is missing: $ControllerLeasePath"
}
$lease = $null
try {
    $lease = [System.IO.File]::Open(
        $ControllerLeasePath,
        [System.IO.FileMode]::Open,
        [System.IO.FileAccess]::ReadWrite,
        [System.IO.FileShare]::None
    )
}
catch {
    throw "Controller lease is not unlocked: $ControllerLeasePath"
}
finally {
    if ($null -ne $lease) { $lease.Dispose() }
}

$stop = Get-Content -Raw -LiteralPath $StopReceiptPath -Encoding utf8 | ConvertFrom-Json -DateKind String -ErrorAction Stop
if ($stop.schema_version -ne 'phase40-telemetry-controlled-stop-v1' -or
    [int]$stop.controller_pid -ne $ExpectedControllerPid -or
    [long]$stop.controller_creation_utc_filetime_ticks -ne $ExpectedControllerCreationUtcFileTimeTicks -or
    [int]$stop.telemetry_pid -ne $ExpectedTelemetryPid -or
    [long]$stop.telemetry_creation_utc_filetime_ticks -ne $ExpectedTelemetryCreationUtcFileTimeTicks -or
    [string]$stop.telemetry_wrapper_sha256 -ne $ExpectedTelemetryWrapperSha256) {
    throw 'Telemetry stop receipt identity mismatch'
}
$stopRequestedAt = ConvertTo-UtcTimestamp -Value ([string]$stop.requested_at_utc) -Context 'stop request'
$telemetryCreatedAt = [DateTimeOffset]([DateTime]::FromFileTimeUtc($ExpectedTelemetryCreationUtcFileTimeTicks))

$chainLines = @(Get-Content -LiteralPath $ChainLogPath -Encoding utf8)
$identityPrefix = "controller_pid=$ExpectedControllerPid controller_creation_utc_filetime_ticks=$ExpectedControllerCreationUtcFileTimeTicks "
$chainRecords = [System.Collections.Generic.List[object]]::new()
foreach ($line in $chainLines) {
    if ($line -notmatch '^(?<timestamp>\S+) (?<message>.*)$') { continue }
    if (-not $Matches.message.StartsWith($identityPrefix, [System.StringComparison]::Ordinal)) { continue }
    $chainRecords.Add([pscustomobject]@{
        Timestamp = ConvertTo-UtcTimestamp -Value $Matches.timestamp -Context 'chain log'
        Message = $Matches.message.Substring($identityPrefix.Length)
    })
}
if ($chainRecords.Count -eq 0) { throw 'Chain log contains no bound controller records' }

$trainerLaunch = @($chainRecords | Where-Object { $_.Message -match "^launched Python operation=phobert-train-fresh child_pid=$ExpectedTrainerPid " })
$trainerExit = @($chainRecords | Where-Object { $_.Message -eq 'phobert-train-fresh exit=0' })
$evidenceVerifications = @($chainRecords | Where-Object { $_.Message -eq 'verify-phobert-run-evidence exit=0' })
$graphExit = @($chainRecords | Where-Object { $_.Message -eq 'render-phobert-graphs exit=0' })
$completeEvidence = @($chainRecords | Where-Object { $_.Message -eq 'Qwen evidence/GGUF verified; full local PhoBERT evidence verified.' })
$terminalFailures = @($chainRecords | Where-Object { $_.Message -eq "terminal failure: PhoBERT telemetry controlled-stop failure: PhoBERT telemetry process failed controlled stop within 30 seconds: pid=$ExpectedTelemetryPid" })
$failedReleases = @($chainRecords | Where-Object { $_.Message -match '^releasing exclusive controller lease .* terminal_status=failed$' })
if ($trainerLaunch.Count -ne 1 -or $trainerExit.Count -ne 1 -or
    $evidenceVerifications.Count -lt 2 -or $graphExit.Count -ne 1 -or
    $completeEvidence.Count -ne 1 -or $terminalFailures.Count -ne 1 -or
    $failedReleases.Count -ne 1) {
    throw 'Chain log does not prove complete run plus isolated telemetry timeout'
}
$finalEvidenceAt = ($evidenceVerifications | Sort-Object Timestamp)[-1].Timestamp
$terminalFailureAt = $terminalFailures[0].Timestamp
$stopToFailureSeconds = ($terminalFailureAt - $stopRequestedAt).TotalSeconds
if ($stopRequestedAt -lt $finalEvidenceAt -or
    $stopToFailureSeconds -lt $stopTimeoutMinimumSeconds -or
    $stopToFailureSeconds -gt $stopTimeoutMaximumSeconds) {
    throw "Stop/terminal timing does not match the controlled 30-second timeout: seconds=$stopToFailureSeconds"
}

$runEvidence = Get-Content -Raw -LiteralPath $RunEvidencePath -Encoding utf8 | ConvertFrom-Json -DateKind String -ErrorAction Stop
$artifactRoles = @($runEvidence.artifacts | ForEach-Object { [string]$_.role })
foreach ($requiredRole in @('events', 'graph_output', 'model_artifact', 'metrics')) {
    if ($artifactRoles -notcontains $requiredRole) {
        throw "Complete run evidence lacks required artifact role: $requiredRole"
    }
}
if ($runEvidence.schema_version -ne 'phase40-run-evidence-v1' -or
    $runEvidence.status -ne 'complete' -or
    $null -ne $runEvidence.failure_reason -or
    $runEvidence.run_id -ne $ExpectedRunId -or
    $runEvidence.selected_checkpoint.safety_gate_passed -ne $true) {
    throw 'Run evidence is not a verified complete safety-passing run'
}

try {
    $rows = @(Import-Csv -LiteralPath $TelemetryCsvPath -Encoding utf8 -ErrorAction Stop)
}
catch {
    throw "Telemetry CSV is malformed: $($_.Exception.Message)"
}
if ($rows.Count -lt 2) { throw "Telemetry CSV requires at least two rows: actual=$($rows.Count)" }
$actualHeaders = @($rows[0].PSObject.Properties.Name)
$headerDiff = @(Compare-Object -ReferenceObject $expectedHeaders -DifferenceObject $actualHeaders -SyncWindow 0)
if ($actualHeaders.Count -ne $expectedHeaders.Count -or $headerDiff.Count -ne 0) {
    throw "Telemetry CSV headers are malformed: $($actualHeaders -join ',')"
}

$parsedRows = [System.Collections.Generic.List[object]]::new()
$observedPids = [System.Collections.Generic.HashSet[long]]::new()
$previousTimestamp = [DateTimeOffset]::MinValue
$previousElapsed = -1.0
$canonicalStartedAt = [DateTimeOffset]::MinValue
$maximumGap = 0.0
$maximumElapsedDelta = 0.0
$postStopSampleCount = 0
for ($rowIndex = 0; $rowIndex -lt $rows.Count; $rowIndex++) {
    $row = $rows[$rowIndex]
    if ([string]::IsNullOrWhiteSpace([string]$row.gpu_name)) {
        throw "Telemetry row $rowIndex has no GPU identity"
    }
    $timestamp = ConvertTo-UtcTimestamp -Value ([string]$row.timestamp_utc) -Context "row $rowIndex timestamp"
    $startedAt = ConvertTo-UtcTimestamp -Value ([string]$row.started_at_utc) -Context "row $rowIndex started_at"
    $elapsed = ConvertFrom-LegacyElapsedNumber -Value ([string]$row.elapsed_seconds) -RowIndex $rowIndex
    if ($rowIndex -eq 0) { $canonicalStartedAt = $startedAt }
    elseif ($startedAt -ne $canonicalStartedAt) { throw "Telemetry started_at changed at row $rowIndex" }
    if ($timestamp -lt $startedAt) { throw "Telemetry timestamp precedes start at row $rowIndex" }
    if ($elapsed -lt $previousElapsed) { throw "Telemetry elapsed regressed at row $rowIndex" }
    $elapsedDelta = [math]::Abs($elapsed - ($timestamp - $startedAt).TotalSeconds)
    if ($elapsedDelta -gt $elapsedToleranceSeconds) {
        throw "Telemetry elapsed differs from timestamp at row ${rowIndex}: delta=$elapsedDelta"
    }
    $maximumElapsedDelta = [math]::Max($maximumElapsedDelta, $elapsedDelta)
    if ($rowIndex -gt 0) {
        $gap = ($timestamp - $previousTimestamp).TotalSeconds
        if ($gap -le 0 -or $gap -gt $maximumAdjacentGapSeconds) {
            throw "Telemetry adjacent gap is invalid at row ${rowIndex}: gap=$gap"
        }
        $maximumGap = [math]::Max($maximumGap, $gap)
    }
    $numbers = [ordered]@{}
    foreach ($field in $numericFields) {
        $numbers[$field] = ConvertFrom-InvariantNonnegativeNumber -Value ([string]$row.$field) -Context "row $rowIndex $field"
    }
    $pidText = [string]$row.python_pid
    if ($pidText -notmatch '^$|^[0-9]+(?:;[0-9]+)*$') {
        throw "Telemetry row $rowIndex has invalid python_pid syntax"
    }
    if (-not [string]::IsNullOrEmpty($pidText)) {
        foreach ($token in $pidText.Split(';')) {
            $parsedPid = 0L
            if (-not [long]::TryParse($token, [ref]$parsedPid) -or $parsedPid -le 0 -or $parsedPid -gt [int]::MaxValue) {
                throw "Telemetry row $rowIndex has invalid python_pid"
            }
            [void]$observedPids.Add($parsedPid)
        }
    }
    if ($timestamp -gt $stopRequestedAt) { $postStopSampleCount++ }
    $parsedRows.Add([pscustomobject]@{ Timestamp=$timestamp; Elapsed=$elapsed; Numbers=[pscustomobject]$numbers })
    $previousTimestamp = $timestamp
    $previousElapsed = $elapsed
}

$firstSampleAt = $parsedRows[0].Timestamp
$lastSampleAt = $parsedRows[-1].Timestamp
$samplerStartDelay = ($canonicalStartedAt - $telemetryCreatedAt).TotalSeconds
$firstSampleDelay = ($firstSampleAt - $telemetryCreatedAt).TotalSeconds
$finalSampleAfterStopSeconds = ($lastSampleAt - $stopRequestedAt).TotalSeconds
if ($samplerStartDelay -lt -5 -or $samplerStartDelay -gt $startupToleranceSeconds -or
    $firstSampleDelay -lt -5 -or $firstSampleDelay -gt $startupToleranceSeconds) {
    throw 'Telemetry startup is not bound to its process creation'
}
if ($firstSampleAt -gt $trainerLaunch[0].Timestamp -or
    $lastSampleAt -lt $finalEvidenceAt -or
    $lastSampleAt -gt $terminalFailureAt -or
    $postStopSampleCount -le 0 -or
    $finalSampleAfterStopSeconds -le 0 -or
    $finalSampleAfterStopSeconds -ge $stopToFailureSeconds) {
    throw 'Telemetry does not continuously cover trainer launch through final verification and bounded forced stop'
}
if ($observedPids.Count -eq 0) { throw 'Telemetry contains no observed related process PID' }

$telemetryItem = Get-Item -LiteralPath $TelemetryCsvPath
$repairScriptSha256 = Get-LowerSha256 -Path $PSCommandPath
$summaryPayload = [ordered]@{
    schema_version = 'phase40-local-system-telemetry-repair-v1'
    model_family = 'phobert'
    run_id = $ExpectedRunId
    run_status = 'complete'
    telemetry_coverage_status = 'complete'
    telemetry_shutdown_status = 'forced_after_controller_timeout'
    telemetry_process_exit_code = $null
    telemetry_process_exit_code_verified = $false
    repair_kind = 'seal_only_no_process_launch'
    detail = 'Model run and graphs verified complete; legacy telemetry coverage recovered without claiming a clean telemetry process exit.'
    sealed_at_utc = [DateTime]::UtcNow.ToString('o')
    sample_count = $rows.Count
    first_sample_utc = $firstSampleAt.ToString('o')
    last_sample_utc = $lastSampleAt.ToString('o')
    elapsed_seconds_encoding = 'legacy-fixed-comma-decimal'
    maximum_observed_adjacent_gap_seconds = $maximumGap
    maximum_observed_elapsed_delta_seconds = $maximumElapsedDelta
    sampler_start_delay_seconds = $samplerStartDelay
    first_sample_delay_seconds = $firstSampleDelay
    stop_to_terminal_failure_seconds = $stopToFailureSeconds
    final_sample_after_stop_seconds = $finalSampleAfterStopSeconds
    post_stop_sample_count = $postStopSampleCount
    observed_python_pids = @($observedPids | Sort-Object)
    peak_vram_used_mib = (@($parsedRows | ForEach-Object { $_.Numbers.vram_used_mib }) | Measure-Object -Maximum).Maximum
    peak_python_rss_bytes = (@($parsedRows | ForEach-Object { $_.Numbers.python_rss_bytes }) | Measure-Object -Maximum).Maximum
    telemetry_csv_path = $TelemetryCsvPath
    telemetry_csv_bytes = $telemetryItem.Length
    telemetry_csv_sha256 = $ExpectedTelemetryCsvSha256
    telemetry_stderr_sha256 = $ExpectedTelemetryStderrSha256
    telemetry_stderr_bytes = 0
    telemetry_stop_receipt_path = $StopReceiptPath
    telemetry_stop_receipt_sha256 = $ExpectedStopReceiptSha256
    telemetry_stop_requested_at_utc = $stopRequestedAt.ToString('o')
    telemetry_pid = $ExpectedTelemetryPid
    telemetry_creation_utc_filetime_ticks = $ExpectedTelemetryCreationUtcFileTimeTicks
    telemetry_wrapper_sha256 = $ExpectedTelemetryWrapperSha256
    controller_pid = $ExpectedControllerPid
    controller_creation_utc_filetime_ticks = $ExpectedControllerCreationUtcFileTimeTicks
    controller_sha256 = $ExpectedControllerSha256
    controller_chain_log_sha256 = $ExpectedChainLogSha256
    controller_terminal_status = 'failed_telemetry_stop_only'
    controller_lease_path = $ControllerLeasePath
    controller_lease_unlocked_verified = $true
    terminal_process_absence_verified = $true
    trainer_pid = $ExpectedTrainerPid
    trainer_exit_code = 0
    run_evidence_sha256 = $ExpectedRunEvidenceSha256
    request_sha256 = $ExpectedRequestSha256
    base_manifest_sha256 = $ExpectedBaseManifestSha256
    repair_script_path = (Get-FullPath $PSCommandPath)
    repair_script_sha256 = $repairScriptSha256
}

if ($CheckOnly) {
    [pscustomobject]@{
        schema_version = 'phase40-local-system-telemetry-repair-check-v1'
        status = 'validated'
        sample_count = $rows.Count
        telemetry_csv_sha256 = $ExpectedTelemetryCsvSha256
        run_evidence_sha256 = $ExpectedRunEvidenceSha256
        repair_script_sha256 = $repairScriptSha256
    } | ConvertTo-Json -Depth 4 -Compress
    exit 0
}

Write-NewJson -Path $SummaryPath -Payload $summaryPayload
$summarySha256 = Get-LowerSha256 -Path $SummaryPath
$summaryReadback = Get-Content -Raw -LiteralPath $SummaryPath -Encoding utf8 | ConvertFrom-Json -DateKind String -ErrorAction Stop
if ($summaryReadback.schema_version -ne 'phase40-local-system-telemetry-repair-v1' -or
    $summaryReadback.run_status -ne 'complete' -or
    $summaryReadback.telemetry_shutdown_status -ne 'forced_after_controller_timeout' -or
    $summaryReadback.telemetry_process_exit_code_verified -ne $false -or
    [int]$summaryReadback.sample_count -ne $rows.Count -or
    $summaryReadback.telemetry_csv_sha256 -ne $ExpectedTelemetryCsvSha256 -or
    $summaryReadback.run_evidence_sha256 -ne $ExpectedRunEvidenceSha256) {
    throw 'Telemetry repair summary readback mismatch'
}

$verificationPayload = [ordered]@{
    schema_version = 'phase40-local-system-telemetry-repair-verification-v1'
    status = 'verified'
    verified_at_utc = [DateTime]::UtcNow.ToString('o')
    run_id = $ExpectedRunId
    telemetry_summary_path = $SummaryPath
    telemetry_summary_sha256 = $summarySha256
    telemetry_csv_path = $TelemetryCsvPath
    telemetry_csv_sha256 = $ExpectedTelemetryCsvSha256
    telemetry_stop_receipt_sha256 = $ExpectedStopReceiptSha256
    run_evidence_sha256 = $ExpectedRunEvidenceSha256
    controller_sha256 = $ExpectedControllerSha256
    controller_chain_log_sha256 = $ExpectedChainLogSha256
    repair_script_sha256 = $repairScriptSha256
    elapsed_seconds_legacy_encoding_verified = $true
    continuous_coverage_verified = $true
    forced_shutdown_truth_preserved = $true
    clean_exit_not_claimed = $true
    terminal_process_absence_verified = $true
    controller_lease_unlocked_verified = $true
    summary_readback_verified = $true
    summary_hash_verified = $true
}
Write-NewJson -Path $VerificationReceiptPath -Payload $verificationPayload
$verificationReadback = Get-Content -Raw -LiteralPath $VerificationReceiptPath -Encoding utf8 | ConvertFrom-Json -DateKind String -ErrorAction Stop
if ($verificationReadback.schema_version -ne 'phase40-local-system-telemetry-repair-verification-v1' -or
    $verificationReadback.status -ne 'verified' -or
    $verificationReadback.telemetry_summary_sha256 -ne $summarySha256 -or
    $verificationReadback.telemetry_csv_sha256 -ne $ExpectedTelemetryCsvSha256 -or
    $verificationReadback.forced_shutdown_truth_preserved -ne $true -or
    $verificationReadback.clean_exit_not_claimed -ne $true) {
    throw 'Telemetry repair verification receipt readback mismatch'
}

foreach ($sealedPath in @($SummaryPath, $VerificationReceiptPath)) {
    $item = Get-Item -LiteralPath $sealedPath
    $item.Attributes = $item.Attributes -bor [System.IO.FileAttributes]::ReadOnly
}

[pscustomobject]@{
    schema_version = 'phase40-local-system-telemetry-repair-result-v1'
    status = 'sealed'
    summary_path = $SummaryPath
    summary_sha256 = $summarySha256
    verification_receipt_path = $VerificationReceiptPath
    verification_receipt_sha256 = Get-LowerSha256 -Path $VerificationReceiptPath
    sample_count = $rows.Count
    repair_script_sha256 = $repairScriptSha256
} | ConvertTo-Json -Depth 4 -Compress
