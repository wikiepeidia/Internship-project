param(
    [int]$QwenSupervisorPid = 1576,
    [int]$QwenTrainerPid = 19772,
    [ValidateRange(0, 0)]
    [int]$MaxResumeAttempts = 0
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$packageRoot = 'D:\PROJEct\AI MODELS\phase40-full-local-20260825'
$sourceRuntime = Join-Path $packageRoot 'source-runtime-v8'
$transferRoot = Join-Path $packageRoot 'transfer-root-v3'
$controllerRoot = Join-Path $packageRoot 'controller'
$requestPath = Join-Path $transferRoot 'data\models\phase40\full-run-request.json'
$sourceArchivePath = Join-Path $transferRoot 'data\models\phase40\source\phase40-source.zip'
$sourceManifestPath = Join-Path $transferRoot 'data\models\phase40\source\phase40-source-manifest.json'
$inputArchive = Join-Path $transferRoot 'data\models\phase40\input\phase40-train-validation.zip'
$inputRoot = 'D:\content\phase40-input-v1'
$baseModelPath = Join-Path $transferRoot 'data\models\phase40\base\phobert-base-v2'
$baseManifestPath = Join-Path $transferRoot 'data\models\phase40\base\phobert-base-v2.provenance.json'
$workParent = Join-Path $packageRoot 'phobert-work-v8'
$workRoot = Join-Path $workParent 'phase40-phobert-full-seed42-v1'
$trainerRoot = Join-Path $workRoot 'trainer'
$runRoot = Join-Path $transferRoot 'data\models\phase40\full\phobert'
$qwenRunRoot = Join-Path $transferRoot 'data\models\phase40\full\qwen-qlora'
$qwenSummaryPath = Join-Path $controllerRoot 'system-telemetry-summary-v3.json'
$qwenGgufManifestPath = Join-Path $packageRoot 'exports-v3\qwen-qlora-q8_0.gguf.manifest.json'
$telemetryScript = Join-Path $controllerRoot 'phase40-system-telemetry-v3.ps1'
$telemetryPath = Join-Path $controllerRoot 'system-telemetry-phobert-v8.csv'
$telemetryStdout = Join-Path $controllerRoot 'telemetry-phobert-v8.stdout.log'
$telemetryStderr = Join-Path $controllerRoot 'telemetry-phobert-v8.stderr.log'
$telemetryStopPath = Join-Path $controllerRoot 'telemetry-phobert-v8.stop.json'
$summaryPath = Join-Path $controllerRoot 'system-telemetry-summary-phobert-v8.json'
$telemetryVerificationReceiptPath = Join-Path $controllerRoot 'system-telemetry-summary-phobert-v8.verification.json'
$chainLog = Join-Path $controllerRoot 'qwen-to-phobert-chain-v8.log'
$runtimePreflightPath = Join-Path $controllerRoot 'source-runtime-preflight-v8.json'
$controllerLeasePath = Join-Path $controllerRoot 'phase40-phobert-chain-controller.lease'
$pythonCacheInstanceId = [Guid]::NewGuid().ToString('N')
$pythonCacheRoot = Join-Path $packageRoot ("python-cache-v8-{0}" -f $pythonCacheInstanceId)
$pythonExe = 'C:\Users\wikiepeidia\AppData\Local\Programs\Python\Python313\python.exe'
$pwshExe = Join-Path $PSHOME 'pwsh.exe'
$runId = 'phase40-phobert-full-seed42-v1'
$expectedRequestSha256 = '2512dbe6d7c5b8c16141ebdbdc848382e56b3a5737e8aeea51d7fb89447c643a'
$expectedSourceArchiveSha256 = 'eae64f17383d749a7759391d766ad59b337d35155ae89744adeaba8631e71a66'
$expectedSourceManifestSha256 = '5903dd5d68881916424e0b529760c3e8810b89a7c207aa714f13171fccf02a3d'
$expectedTelemetryScriptSha256 = '1bc33f3726b57297a3cc5a69b36831bbd602edac680ba329224b14cf06231c70'
$expectedSourceFileCount = 28
$telemetrySamplerIntervalSeconds = 10
$telemetryStartedAtToleranceSeconds = 10
$telemetryFirstSampleToleranceSeconds = 30
$telemetryMaxAdjacentGapSeconds = 30
$telemetryElapsedToleranceSeconds = 5
$telemetryClockSkewToleranceSeconds = 5
$controllerPid = $PID
$controllerProcess = [System.Diagnostics.Process]::GetCurrentProcess()
$controllerCreationUtc = $controllerProcess.StartTime.ToUniversalTime()
$controllerCreationUtcFileTimeTicks = $controllerCreationUtc.ToFileTimeUtc()
$controllerSha256 = (Get-FileHash -LiteralPath $PSCommandPath -Algorithm SHA256).Hash.ToLowerInvariant()
$controllerLeaseMeaning = 'Exclusive live-controller lease retained with FileShare.None for the full controller lifetime.'
$controllerLeaseStream = $null
$pythonLaunchPreflightSequence = 0

# Keep bytecode outside the frozen source tree. Python must never consume an
# adjacent __pycache__ that is absent from the source inventory.
$env:PYTHONPYCACHEPREFIX = $pythonCacheRoot
$env:PYTHONDONTWRITEBYTECODE = '1'

function Write-ChainLog {
    param([Parameter(Mandatory)][string]$Message)
    Assert-ControllerLeaseHeld
    $line = "{0} controller_pid={1} controller_creation_utc_filetime_ticks={2} {3}" -f `
        [DateTime]::UtcNow.ToString('o'),
        $controllerPid,
        $controllerCreationUtcFileTimeTicks,
        $Message
    Add-Content -LiteralPath $chainLog -Value $line -Encoding utf8NoBOM
}

function Get-LowerSha256 {
    param([Parameter(Mandatory)][string]$Path)
    return (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLowerInvariant()
}

function Get-LowerSha256FromBytes {
    param([Parameter(Mandatory)][byte[]]$Bytes)
    $algorithm = [System.Security.Cryptography.SHA256]::Create()
    try {
        return ([Convert]::ToHexString($algorithm.ComputeHash($Bytes))).ToLowerInvariant()
    }
    finally {
        $algorithm.Dispose()
    }
}

function Assert-ControllerLeaseHeld {
    if ($null -eq $script:controllerLeaseStream -or
        -not $script:controllerLeaseStream.CanRead -or
        -not $script:controllerLeaseStream.CanWrite -or
        $script:controllerLeaseStream.SafeFileHandle.IsClosed -or
        $script:controllerLeaseStream.SafeFileHandle.IsInvalid) {
        throw 'The exclusive Phase 40 controller lease is not held by this process'
    }
}

function Open-ControllerLease {
    $leaseStream = $null
    try {
        $leaseControllerSha256 = Get-LowerSha256 -Path $PSCommandPath
        if ($leaseControllerSha256 -ne $controllerSha256) {
            throw "Controller source SHA-256 changed before lease acquisition: $leaseControllerSha256"
        }
        # OpenOrCreate permits a stale on-disk receipt, but FileShare.None makes a
        # second live controller fail here before it can preflight or write logs.
        $leaseStream = [System.IO.FileStream]::new(
            $controllerLeasePath,
            [System.IO.FileMode]::OpenOrCreate,
            [System.IO.FileAccess]::ReadWrite,
            [System.IO.FileShare]::None,
            4096,
            [System.IO.FileOptions]::WriteThrough
        )
        $leasePayload = [ordered]@{
            schema_version = 'phase40-controller-exclusive-lease-v1'
            acquired_at_utc = [DateTime]::UtcNow.ToString('o')
            controller_pid = $controllerPid
            controller_creation_utc = $controllerCreationUtc.ToString('o')
            controller_creation_utc_filetime_ticks = $controllerCreationUtcFileTimeTicks
            controller_sha256 = $leaseControllerSha256
            controller_lease_path = $controllerLeasePath
            controller_lease_held = $true
            controller_lease_file_share = 'none'
            controller_lease_meaning = $controllerLeaseMeaning
        }
        $leaseJson = ($leasePayload | ConvertTo-Json -Depth 4) + [Environment]::NewLine
        $leaseBytes = [System.Text.UTF8Encoding]::new($false).GetBytes($leaseJson)
        $leaseStream.SetLength(0)
        $leaseStream.Position = 0
        $leaseStream.Write($leaseBytes, 0, $leaseBytes.Length)
        $leaseStream.Flush($true)
        return $leaseStream
    }
    catch {
        if ($null -ne $leaseStream) {
            $leaseStream.Dispose()
        }
        throw "Unable to acquire exclusive Phase 40 controller lease at ${controllerLeasePath}: $($_.Exception.Message)"
    }
}

function Assert-TelemetryScriptIdentity {
    if (-not (Test-Path -LiteralPath $telemetryScript -PathType Leaf)) {
        throw "Telemetry script is missing: $telemetryScript"
    }
    $telemetryItem = Get-Item -LiteralPath $telemetryScript
    if ($telemetryItem.Attributes -band [System.IO.FileAttributes]::ReparsePoint) {
        throw 'Telemetry script cannot be a reparse point'
    }
    $telemetrySha256 = Get-LowerSha256 -Path $telemetryScript
    if ($telemetrySha256 -ne $expectedTelemetryScriptSha256) {
        throw "Telemetry script SHA-256 changed: $telemetrySha256"
    }
    $parseErrors = $null
    $parseTokens = $null
    [void][System.Management.Automation.Language.Parser]::ParseFile(
        $telemetryScript,
        [ref]$parseTokens,
        [ref]$parseErrors
    )
    if ($parseErrors.Count -ne 0) {
        throw "Telemetry script PowerShell parse failed: $($parseErrors[0].Message)"
    }
    return [pscustomobject]@{
        Sha256 = $telemetrySha256
        ParseTokenCount = $parseTokens.Count
        ParseErrorCount = 0
    }
}

function Assert-FrozenSourceRuntime {
    param(
        [Parameter(Mandatory)]
        [ValidateSet('armed', 'prelaunch', 'python-launch')]
        [string]$Stage,
        [string]$OperationName = ''
    )

    Assert-ControllerLeaseHeld
    if ($Stage -eq 'python-launch' -and [string]::IsNullOrWhiteSpace($OperationName)) {
        throw 'Python-launch source preflight requires an operation name'
    }
    if ($Stage -ne 'python-launch' -and -not [string]::IsNullOrEmpty($OperationName)) {
        throw "OperationName is only valid for a python-launch preflight: $Stage"
    }

    # With bytecode writes disabled this GUID-scoped path must remain absent.
    # Its absence proves this controller cannot consume a pre-existing cache.
    if (Test-Path -LiteralPath $pythonCacheRoot) {
        throw "Python bytecode cache path exists at $Stage preflight: $pythonCacheRoot"
    }

    foreach ($requiredFile in @($requestPath, $sourceArchivePath, $sourceManifestPath)) {
        if (-not (Test-Path -LiteralPath $requiredFile -PathType Leaf)) {
            throw "Frozen source preflight is missing: $requiredFile"
        }
    }
    if (-not (Test-Path -LiteralPath $sourceRuntime -PathType Container)) {
        throw "Frozen source runtime is missing: $sourceRuntime"
    }
    $runtimeItem = Get-Item -LiteralPath $sourceRuntime
    if ($runtimeItem.Attributes -band [System.IO.FileAttributes]::ReparsePoint) {
        throw 'Frozen source runtime cannot be a reparse point'
    }
    $unsafeItems = @(
        Get-ChildItem -LiteralPath $sourceRuntime -Recurse -Force |
            Where-Object { $_.Attributes -band [System.IO.FileAttributes]::ReparsePoint }
    )
    if ($unsafeItems.Count -ne 0) {
        throw "Frozen source runtime contains a reparse point: $($unsafeItems[0].FullName)"
    }

    $requestSha256 = Get-LowerSha256 -Path $requestPath
    $archiveSha256 = Get-LowerSha256 -Path $sourceArchivePath
    $manifestSha256 = Get-LowerSha256 -Path $sourceManifestPath
    $telemetryIdentity = Assert-TelemetryScriptIdentity
    $currentControllerSha256 = Get-LowerSha256 -Path $PSCommandPath
    if ($currentControllerSha256 -ne $controllerSha256) {
        throw "Controller source SHA-256 changed after lease acquisition: $currentControllerSha256"
    }
    if ($requestSha256 -ne $expectedRequestSha256) {
        throw "Run-request SHA-256 changed: $requestSha256"
    }
    if ($archiveSha256 -ne $expectedSourceArchiveSha256) {
        throw "Source archive SHA-256 changed: $archiveSha256"
    }
    if ($manifestSha256 -ne $expectedSourceManifestSha256) {
        throw "Source manifest SHA-256 changed: $manifestSha256"
    }

    $request = Get-Content -LiteralPath $requestPath -Raw -Encoding utf8 | ConvertFrom-Json
    $manifest = Get-Content -LiteralPath $sourceManifestPath -Raw -Encoding utf8 | ConvertFrom-Json
    if ($request.source_bundle.archive_sha256 -ne $expectedSourceArchiveSha256 -or
        $request.source_bundle.inventory_sha256 -ne $expectedSourceManifestSha256 -or
        $manifest.archive_sha256 -ne $expectedSourceArchiveSha256) {
        throw 'Run request, source archive, and source manifest do not share one identity'
    }
    $manifestFiles = @($manifest.files)
    if ($manifestFiles.Count -ne $expectedSourceFileCount) {
        throw "Frozen source manifest file count changed: expected=$expectedSourceFileCount actual=$($manifestFiles.Count)"
    }

    $runtimePrefix = $sourceRuntime.TrimEnd([System.IO.Path]::DirectorySeparatorChar) +
        [System.IO.Path]::DirectorySeparatorChar
    $expectedByPath = @{}
    foreach ($entry in $manifestFiles) {
        $relative = [string]$entry.path
        if ([System.IO.Path]::IsPathRooted($relative) -or
            $relative.Split('/') -contains '..' -or
            $expectedByPath.ContainsKey($relative)) {
            throw "Unsafe or duplicate source inventory path: $relative"
        }
        $candidate = [System.IO.Path]::GetFullPath(
            (Join-Path $sourceRuntime $relative.Replace('/', [System.IO.Path]::DirectorySeparatorChar))
        )
        if (-not $candidate.StartsWith($runtimePrefix, [System.StringComparison]::OrdinalIgnoreCase)) {
            throw "Source inventory path escaped its runtime root: $relative"
        }
        if (-not (Test-Path -LiteralPath $candidate -PathType Leaf)) {
            throw "Source inventory file is missing: $relative"
        }
        $item = Get-Item -LiteralPath $candidate
        $actualSha256 = Get-LowerSha256 -Path $candidate
        if ($item.Length -ne [long]$entry.bytes -or $actualSha256 -ne [string]$entry.sha256) {
            throw "Source runtime identity mismatch: $relative"
        }
        $expectedByPath[$relative] = $actualSha256
    }

    $actualFiles = @(Get-ChildItem -LiteralPath $sourceRuntime -Recurse -File -Force)
    if ($actualFiles.Count -ne $expectedByPath.Count) {
        throw "Source runtime file count differs: expected=$($expectedByPath.Count) actual=$($actualFiles.Count)"
    }
    foreach ($file in $actualFiles) {
        $relative = [System.IO.Path]::GetRelativePath($sourceRuntime, $file.FullName).Replace('\', '/')
        if (-not $expectedByPath.ContainsKey($relative)) {
            throw "Source runtime contains an unlisted file: $relative"
        }
    }

    $pythonLaunchSequence = $null
    if ($Stage -eq 'python-launch') {
        $script:pythonLaunchPreflightSequence++
        $pythonLaunchSequence = $script:pythonLaunchPreflightSequence
        $safeOperationName = [regex]::Replace($OperationName, '[^A-Za-z0-9._-]', '_')
        $stagePath = Join-Path $controllerRoot (
            'source-runtime-preflight-v8-python-launch-{0}-{1}-{2:D3}-{3}.json' -f
                $controllerPid,
                $controllerCreationUtcFileTimeTicks,
                $pythonLaunchSequence,
                $safeOperationName
        )
    }
    else {
        $stagePath = Join-Path $controllerRoot "source-runtime-preflight-v8-$Stage.json"
    }
    $payload = [ordered]@{
        schema_version = 'phase40-source-runtime-preflight-v3'
        stage = $Stage
        operation_name = if ($Stage -eq 'python-launch') { $OperationName } else { $null }
        python_launch_sequence = $pythonLaunchSequence
        verified_at_utc = [DateTime]::UtcNow.ToString('o')
        controller_pid = $controllerPid
        controller_creation_utc = $controllerCreationUtc.ToString('o')
        controller_creation_utc_filetime_ticks = $controllerCreationUtcFileTimeTicks
        controller_sha256 = $currentControllerSha256
        controller_lease_path = $controllerLeasePath
        controller_lease_held = $true
        controller_lease_file_share = 'none'
        controller_lease_meaning = $controllerLeaseMeaning
        request_sha256 = $requestSha256
        source_archive_sha256 = $archiveSha256
        source_manifest_sha256 = $manifestSha256
        source_runtime = $sourceRuntime
        source_file_count = $actualFiles.Count
        expected_source_file_count = $expectedSourceFileCount
        telemetry_script = $telemetryScript
        telemetry_script_sha256 = $telemetryIdentity.Sha256
        telemetry_script_parse_token_count = $telemetryIdentity.ParseTokenCount
        telemetry_script_parse_error_count = $telemetryIdentity.ParseErrorCount
        python_cache_instance_id = $pythonCacheInstanceId
        python_cache_root = $pythonCacheRoot
        python_cache_root_absent = $true
        adjacent_bytecode_cache_allowed = $false
        reserved_split_access_attempted_by_controller = $false
    }
    $payload | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath $stagePath -Encoding utf8NoBOM
    if ($Stage -eq 'armed') {
        $payload | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath $runtimePreflightPath -Encoding utf8NoBOM
    }
    Write-ChainLog "frozen source runtime verified stage=$Stage operation=$OperationName files=$($actualFiles.Count) telemetry_sha256=$($telemetryIdentity.Sha256) telemetry_parse_errors=0 python_cache_root_absent=true lease_held=true receipt=$stagePath"
    return $stagePath
}

function Invoke-PythonCaptured {
    param(
        [Parameter(Mandatory)][string[]]$Arguments,
        [Parameter(Mandatory)][string]$Name
    )
    $stdoutPath = Join-Path $controllerRoot "$Name.phobert-v8.stdout.log"
    $stderrPath = Join-Path $controllerRoot "$Name.phobert-v8.stderr.log"
    $startInfo = [System.Diagnostics.ProcessStartInfo]::new()
    $startInfo.FileName = $pythonExe
    $startInfo.WorkingDirectory = $sourceRuntime
    $startInfo.UseShellExecute = $false
    $startInfo.CreateNoWindow = $true
    $startInfo.RedirectStandardOutput = $true
    $startInfo.RedirectStandardError = $true
    foreach ($argument in $Arguments) {
        [void]$startInfo.ArgumentList.Add($argument)
    }
    $process = [System.Diagnostics.Process]::new()
    $process.StartInfo = $startInfo
    Write-ChainLog "preparing Python launch operation=$Name"
    # This is deliberately the last operation before Process.Start: every
    # Python child gets a newly retained, full 28-file runtime preflight.
    $pythonLaunchPreflightPath = Assert-FrozenSourceRuntime `
        -Stage 'python-launch' `
        -OperationName $Name
    if (-not $process.Start()) {
        throw "Failed to start $Name"
    }
    Write-ChainLog "launched Python operation=$Name child_pid=$($process.Id) preflight=$pythonLaunchPreflightPath"
    $stdoutTask = $process.StandardOutput.ReadToEndAsync()
    $stderrTask = $process.StandardError.ReadToEndAsync()
    $process.WaitForExit()
    [System.IO.File]::WriteAllText(
        $stdoutPath,
        $stdoutTask.GetAwaiter().GetResult(),
        [System.Text.UTF8Encoding]::new($false)
    )
    [System.IO.File]::WriteAllText(
        $stderrPath,
        $stderrTask.GetAwaiter().GetResult(),
        [System.Text.UTF8Encoding]::new($false)
    )
    Write-ChainLog "$Name exit=$($process.ExitCode)"
    return $process.ExitCode
}

function Assert-QwenCompletion {
    if (-not (Test-Path -LiteralPath $qwenSummaryPath -PathType Leaf)) {
        throw 'Qwen supervisor exited without its final telemetry summary'
    }
    $summary = Get-Content -LiteralPath $qwenSummaryPath -Raw -Encoding utf8 |
        ConvertFrom-Json
    if ($summary.status -ne 'complete') {
        throw "Qwen terminal status is not complete: $($summary.status) $($summary.detail)"
    }
    $qwenVerifyExit = Invoke-PythonCaptured -Name 'verify-qwen-before-phobert' -Arguments @(
        '-m', 'src.model_adaptation.phase40_operator',
        'phase40-verify-run-evidence',
        '--run-root', $qwenRunRoot
    )
    if ($qwenVerifyExit -ne 0) {
        throw 'Qwen run-evidence verification failed before PhoBERT'
    }
    $ggufVerifyExit = Invoke-PythonCaptured -Name 'verify-qwen-gguf-before-phobert' -Arguments @(
        '-m', 'src.model_adaptation.phase40_gguf', 'verify',
        '--manifest-path', $qwenGgufManifestPath
    )
    if ($ggufVerifyExit -ne 0) {
        throw 'Qwen GGUF verification failed before PhoBERT'
    }
}

function Wait-QwenGpuRelease {
    param([long]$TrainerStartTicks)
    $deadline = [DateTime]::UtcNow.AddMinutes(20)
    $safeSamples = 0
    while ([DateTime]::UtcNow -lt $deadline) {
        $trainer = Get-Process -Id $QwenTrainerPid -ErrorAction SilentlyContinue
        $sameTrainerAlive = $null -ne $trainer -and
            $TrainerStartTicks -ne 0 -and
            $trainer.StartTime.ToUniversalTime().Ticks -eq $TrainerStartTicks
        $gpuLine = & nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits 2>$null
        if ($LASTEXITCODE -ne 0 -or -not $gpuLine) {
            throw 'Unable to verify GPU memory release after Qwen'
        }
        $firstGpuLine = if ($gpuLine -is [array]) { [string]$gpuLine[0] } else { [string]$gpuLine }
        $usedMiB = [int]$firstGpuLine.Trim()
        if (-not $sameTrainerAlive -and $usedMiB -le 2048) {
            $safeSamples++
            if ($safeSamples -ge 3) {
                Write-ChainLog "Qwen GPU released used_mib=$usedMiB safe_samples=$safeSamples"
                return
            }
        }
        else {
            $safeSamples = 0
        }
        Start-Sleep -Seconds 15
    }
    throw 'GPU did not return below 2048 MiB for three samples within 20 minutes after Qwen'
}

function Invoke-PhoBertDoctor {
    return Invoke-PythonCaptured -Name 'phobert-doctor' -Arguments @(
        '-m', 'src.model_adaptation.phase40_operator',
        'phase40-doctor',
        '--model-family', 'phobert',
        '--adaptation-mode', 'classification-head',
        '--run-kind', 'full',
        '--model-revision', 'e966aac8cb889325e073aa5f28ff70aca4dbc8c3',
        '--run-request-path', '..\transfer-root-v3\data\models\phase40\full-run-request.json',
        '--repo-root', '..\transfer-root-v3',
        '--input-root', 'D:\content\phase40-input-v1',
        '--base-model-path', '..\transfer-root-v3\data\models\phase40\base\phobert-base-v2',
        '--base-model-manifest-path', '..\transfer-root-v3\data\models\phase40\base\phobert-base-v2.provenance.json'
    )
}

function Invoke-PhoBertTraining {
    param([string]$ResumeFromCheckpoint = $null, [string]$Name = 'phobert-train-fresh')
    $arguments = [System.Collections.Generic.List[string]]::new()
    foreach ($argument in @(
        '-m', 'src.model_adaptation.phase40_operator',
        'phase40-train-phobert',
        '--request-path', '..\transfer-root-v3\data\models\phase40\full-run-request.json',
        '--repo-root', '..\transfer-root-v3',
        '--input-archive', '..\transfer-root-v3\data\models\phase40\input\phase40-train-validation.zip',
        '--extraction-root', '/content/phase40-input-v1',
        '--run-id', $runId,
        '--output-root', '..\phobert-work-v8\phase40-phobert-full-seed42-v1',
        '--base-model-path', '..\transfer-root-v3\data\models\phase40\base\phobert-base-v2',
        '--base-model-manifest-path', '..\transfer-root-v3\data\models\phase40\base\phobert-base-v2.provenance.json'
    )) {
        [void]$arguments.Add($argument)
    }
    if ($null -ne $ResumeFromCheckpoint) {
        [void]$arguments.Add('--resume-from-checkpoint')
        [void]$arguments.Add([System.IO.Path]::GetFullPath($ResumeFromCheckpoint))
    }
    return Invoke-PythonCaptured -Name $Name -Arguments $arguments.ToArray()
}

function Test-PhoBertRunComplete {
    $name = 'verify-phobert-run-evidence'
    $exitCode = Invoke-PythonCaptured -Name $name -Arguments @(
        '-m', 'src.model_adaptation.phase40_operator',
        'phase40-verify-run-evidence',
        '--run-root', $runRoot
    )
    if ($exitCode -ne 0) {
        return $false
    }
    $stdoutPath = Join-Path $controllerRoot "$name.phobert-v8.stdout.log"
    try {
        $payload = Get-Content -LiteralPath $stdoutPath -Raw -Encoding utf8 |
            ConvertFrom-Json
    }
    catch {
        return $false
    }
    return $payload.status -eq 'complete'
}

function Invoke-PhoBertRenderGraphs {
    return Invoke-PythonCaptured -Name 'render-phobert-graphs' -Arguments @(
        '-m', 'src.model_adaptation.phase40_operator',
        'phase40-render-graphs',
        '--run-root', $runRoot
    )
}

function Get-LatestPhoBertCheckpoint {
    if (-not (Test-Path -LiteralPath $trainerRoot -PathType Container)) {
        return $null
    }
    $candidates = @(
        Get-ChildItem -LiteralPath $trainerRoot -Directory -Filter 'checkpoint-*' |
            Where-Object {
                -not ($_.Attributes -band [System.IO.FileAttributes]::ReparsePoint) -and
                (Test-Path -LiteralPath (Join-Path $_.FullName 'phase40-resume-manifest.json') -PathType Leaf)
            } |
            ForEach-Object {
                if ($_.Name -match '^checkpoint-([0-9]+)$') {
                    [pscustomobject]@{ Path = $_.FullName; Step = [int]$Matches[1] }
                }
            } |
            Sort-Object Step -Descending
    )
    if ($candidates.Count -eq 0) {
        return $null
    }
    return $candidates[0]
}

function Invoke-VerifiedPhoBertResume {
    param([Parameter(Mandatory)]$Checkpoint, [Parameter(Mandatory)][int]$Attempt)
    $verifyExit = Invoke-PythonCaptured -Name "verify-phobert-resume-$Attempt" -Arguments @(
        '-m', 'src.model_adaptation.phase40_operator',
        'phase40-verify-resume',
        '--request-path', $requestPath,
        '--repo-root', $transferRoot,
        '--run-id', $runId,
        '--checkpoint', $Checkpoint.Path,
        '--input-root', $inputRoot,
        '--base-model-path', $baseModelPath,
        '--base-model-manifest-path', $baseManifestPath
    )
    if ($verifyExit -ne 0) {
        throw "PhoBERT checkpoint $($Checkpoint.Path) failed exact resume verification"
    }
    Write-ChainLog "PhoBERT resume attempt=$Attempt checkpoint_step=$($Checkpoint.Step)"
    return Invoke-PhoBertTraining -ResumeFromCheckpoint $Checkpoint.Path -Name "phobert-resume-$Attempt"
}

function Start-PhoBertTelemetry {
    $telemetryIdentity = Assert-TelemetryScriptIdentity
    foreach ($freshTelemetryPath in @(
        $telemetryPath,
        $telemetryStdout,
        $telemetryStderr,
        $telemetryStopPath,
        $summaryPath,
        $telemetryVerificationReceiptPath
    )) {
        if (Test-Path -LiteralPath $freshTelemetryPath) {
            throw "Refusing non-fresh telemetry artifact: $freshTelemetryPath"
        }
    }

    # The frozen telemetry script is an intentional infinite sampler. Run it in
    # an asynchronous in-process pipeline owned by a small PowerShell wrapper so
    # a durable stop receipt can cancel the pipeline and let the wrapper exit 0.
    # Any early completion or pre-stop pipeline error exits nonzero on stderr.
    $scriptPathBase64 = [Convert]::ToBase64String(
        [System.Text.UTF8Encoding]::new($false).GetBytes($telemetryScript)
    )
    $outputPathBase64 = [Convert]::ToBase64String(
        [System.Text.UTF8Encoding]::new($false).GetBytes($telemetryPath)
    )
    $stopPathBase64 = [Convert]::ToBase64String(
        [System.Text.UTF8Encoding]::new($false).GetBytes($telemetryStopPath)
    )
    $wrapperScript = @"
`$ErrorActionPreference = 'Stop'
`$utf8 = [System.Text.UTF8Encoding]::new(`$false)
`$scriptPath = `$utf8.GetString([Convert]::FromBase64String('$scriptPathBase64'))
`$outputPath = `$utf8.GetString([Convert]::FromBase64String('$outputPathBase64'))
`$stopPath = `$utf8.GetString([Convert]::FromBase64String('$stopPathBase64'))
`$expectedSha256 = '$($telemetryIdentity.Sha256)'
`$engine = [System.Management.Automation.PowerShell]::Create()
try {
    `$actualSha256 = (Get-FileHash -LiteralPath `$scriptPath -Algorithm SHA256).Hash.ToLowerInvariant()
    if (`$actualSha256 -ne `$expectedSha256) {
        throw "Telemetry script SHA-256 changed inside wrapper: `$actualSha256"
    }
    [void]`$engine.AddCommand(`$scriptPath)
    [void]`$engine.AddParameter('OutputPath', `$outputPath)
    [void]`$engine.AddParameter('IntervalSeconds', $telemetrySamplerIntervalSeconds)
    `$async = `$engine.BeginInvoke()
    while (-not (Test-Path -LiteralPath `$stopPath -PathType Leaf)) {
        if (`$async.IsCompleted) {
            try { [void]`$engine.EndInvoke(`$async) } catch {
                [Console]::Error.WriteLine(`$_.Exception.ToString())
                exit 21
            }
            foreach (`$record in @(`$engine.Streams.Error)) {
                [Console]::Error.WriteLine(`$record.ToString())
            }
            [Console]::Error.WriteLine('Telemetry pipeline exited before a controlled stop request')
            exit 22
        }
        Start-Sleep -Milliseconds 250
    }
    `$preStopErrors = @(`$engine.Streams.Error)
    if (`$preStopErrors.Count -ne 0) {
        foreach (`$record in `$preStopErrors) {
            [Console]::Error.WriteLine(`$record.ToString())
        }
        exit 23
    }
    try { `$engine.Stop() } catch {
        [Console]::Error.WriteLine(`$_.Exception.ToString())
        exit 24
    }
    try { [void]`$engine.EndInvoke(`$async) } catch {
        `$expectedCancellation =
            `$_.Exception -is [System.Management.Automation.PipelineStoppedException] -or
            `$_.Exception.InnerException -is [System.Management.Automation.PipelineStoppedException] -or
            `$_.FullyQualifiedErrorId -match 'PipelineStopped'
        if (-not `$expectedCancellation) {
            [Console]::Error.WriteLine(`$_.Exception.ToString())
            exit 26
        }
    }
    exit 0
}
catch {
    [Console]::Error.WriteLine(`$_.Exception.ToString())
    exit 25
}
finally {
    `$engine.Dispose()
}
"@
    $wrapperBytes = [System.Text.Encoding]::Unicode.GetBytes($wrapperScript)
    $wrapperSha256 = Get-LowerSha256FromBytes -Bytes $wrapperBytes
    $encodedCommand = [Convert]::ToBase64String($wrapperBytes)
    $argumentString = "-NoLogo -NoProfile -NonInteractive -EncodedCommand $encodedCommand"
    Write-ChainLog "telemetry script and wrapper verified immediately before launch script_sha256=$($telemetryIdentity.Sha256) wrapper_sha256=$wrapperSha256 parse_errors=0"
    $process = Start-Process -FilePath $pwshExe -ArgumentList $argumentString `
        -WorkingDirectory $controllerRoot -WindowStyle Hidden `
        -RedirectStandardOutput $telemetryStdout `
        -RedirectStandardError $telemetryStderr -PassThru
    $process | Add-Member -NotePropertyName Phase40WrapperSha256 -NotePropertyValue $wrapperSha256
    return $process
}

function Stop-PhoBertTelemetry {
    param([Parameter(Mandatory)]$TelemetryProcess)
    $live = Get-Process -Id $TelemetryProcess.Id -ErrorAction SilentlyContinue
    if ($null -eq $live) {
        throw "PhoBERT telemetry process exited before controlled stop: pid=$($TelemetryProcess.Id)"
    }
    $expectedStartFileTime = $TelemetryProcess.StartTime.ToUniversalTime().ToFileTimeUtc()
    $actualStartFileTime = $live.StartTime.ToUniversalTime().ToFileTimeUtc()
    if ($actualStartFileTime -ne $expectedStartFileTime) {
        throw "Refusing to stop reused PID $($TelemetryProcess.Id)"
    }
    if (Test-Path -LiteralPath $telemetryStopPath) {
        throw "Telemetry stop receipt already exists: $telemetryStopPath"
    }
    $stopRequestedAtUtc = [DateTime]::UtcNow.ToString('o')
    $stopPayload = [ordered]@{
        schema_version = 'phase40-telemetry-controlled-stop-v1'
        requested_at_utc = $stopRequestedAtUtc
        controller_pid = $controllerPid
        controller_creation_utc_filetime_ticks = $controllerCreationUtcFileTimeTicks
        telemetry_pid = $TelemetryProcess.Id
        telemetry_creation_utc_filetime_ticks = $expectedStartFileTime
        telemetry_wrapper_sha256 = $TelemetryProcess.Phase40WrapperSha256
        stop_reason = 'terminal telemetry evidence seal'
    }
    $stopJson = ($stopPayload | ConvertTo-Json -Depth 4) + [Environment]::NewLine
    $stopBytes = [System.Text.UTF8Encoding]::new($false).GetBytes($stopJson)
    $stopStream = [System.IO.FileStream]::new(
        $telemetryStopPath,
        [System.IO.FileMode]::CreateNew,
        [System.IO.FileAccess]::Write,
        [System.IO.FileShare]::Read,
        4096,
        [System.IO.FileOptions]::WriteThrough
    )
    try {
        $stopStream.Write($stopBytes, 0, $stopBytes.Length)
        $stopStream.Flush($true)
    }
    finally {
        $stopStream.Dispose()
    }
    if (-not $TelemetryProcess.WaitForExit(30000)) {
        $stillLive = Get-Process -Id $TelemetryProcess.Id -ErrorAction SilentlyContinue
        if ($null -ne $stillLive -and
            $stillLive.StartTime.ToUniversalTime().ToFileTimeUtc() -eq $expectedStartFileTime) {
            Stop-Process -Id $TelemetryProcess.Id -Force
            [void]$TelemetryProcess.WaitForExit(10000)
        }
        throw "PhoBERT telemetry process failed controlled stop within 30 seconds: pid=$($TelemetryProcess.Id)"
    }
    $TelemetryProcess.Refresh()
    if ($TelemetryProcess.ExitCode -ne 0) {
        throw "PhoBERT telemetry process exited nonzero: pid=$($TelemetryProcess.Id) exit=$($TelemetryProcess.ExitCode)"
    }
    if (-not (Test-Path -LiteralPath $telemetryStderr -PathType Leaf)) {
        throw "PhoBERT telemetry stderr capture is missing: $telemetryStderr"
    }
    $stderrItem = Get-Item -LiteralPath $telemetryStderr
    if ($stderrItem.Length -ne 0) {
        throw "PhoBERT telemetry stderr is not empty: bytes=$($stderrItem.Length) path=$telemetryStderr"
    }
    $receipt = [pscustomobject]@{
        telemetry_pid = $TelemetryProcess.Id
        telemetry_creation_utc_filetime_ticks = $expectedStartFileTime
        telemetry_exit_code = $TelemetryProcess.ExitCode
        telemetry_wrapper_sha256 = $TelemetryProcess.Phase40WrapperSha256
        telemetry_stderr_bytes = $stderrItem.Length
        telemetry_stderr_sha256 = Get-LowerSha256 -Path $telemetryStderr
        telemetry_stop_receipt_sha256 = Get-LowerSha256 -Path $telemetryStopPath
        telemetry_stop_requested_at_utc = $stopRequestedAtUtc
    }
    Write-ChainLog "controlled PhoBERT telemetry stop verified pid=$($receipt.telemetry_pid) exit=0 stderr_bytes=0 stop_receipt_sha256=$($receipt.telemetry_stop_receipt_sha256)"
    return $receipt
}

function Write-PhoBertTelemetrySeal {
    param(
        [Parameter(Mandatory)][ValidateSet('complete', 'failed')][string]$Status,
        [string]$Detail = '',
        [Parameter(Mandatory)]$StopReceipt
    )
    if (-not (Test-Path -LiteralPath $telemetryPath -PathType Leaf)) {
        throw "PhoBERT telemetry CSV is missing: $telemetryPath"
    }
    $telemetryItem = Get-Item -LiteralPath $telemetryPath
    if ($telemetryItem.Length -eq 0) {
        throw "PhoBERT telemetry CSV is empty: $telemetryPath"
    }
    try {
        $rows = @(Import-Csv -LiteralPath $telemetryPath -Encoding utf8 -ErrorAction Stop)
    }
    catch {
        throw "PhoBERT telemetry CSV is malformed: $($_.Exception.Message)"
    }
    if ($rows.Count -lt 2) {
        throw "PhoBERT telemetry CSV requires at least two data rows: actual=$($rows.Count) path=$telemetryPath"
    }
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
    $actualHeaders = @($rows[0].PSObject.Properties.Name)
    if ($actualHeaders.Count -ne $expectedHeaders.Count -or
        (Compare-Object -ReferenceObject $expectedHeaders -DifferenceObject $actualHeaders -SyncWindow 0)) {
        throw "PhoBERT telemetry CSV headers are malformed: $($actualHeaders -join ',')"
    }
    $numericFields = @(
        'elapsed_seconds',
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
    $numericRows = [System.Collections.Generic.List[object]]::new()
    $parsedTimestamps = [System.Collections.Generic.List[DateTimeOffset]]::new()
    $observedPythonPids = [System.Collections.Generic.HashSet[long]]::new()
    $pythonPidNonemptySampleCount = 0
    $previousElapsed = -1.0
    $previousTimestamp = [DateTimeOffset]::MinValue
    $canonicalStartedAt = [DateTimeOffset]::MinValue
    $maximumObservedAdjacentGapSeconds = 0.0
    $maximumObservedElapsedDeltaSeconds = 0.0
    try {
        $telemetryProcessStartedAt = [DateTimeOffset]::new(
            [DateTime]::FromFileTimeUtc(
                [long]$StopReceipt.telemetry_creation_utc_filetime_ticks
            )
        )
    }
    catch {
        throw "PhoBERT telemetry process creation FILETIME is invalid: $($_.Exception.Message)"
    }
    for ($rowIndex = 0; $rowIndex -lt $rows.Count; $rowIndex++) {
        $row = $rows[$rowIndex]
        if ([string]::IsNullOrWhiteSpace([string]$row.gpu_name)) {
            throw "PhoBERT telemetry row $rowIndex has no GPU identity"
        }
        $parsedDates = @{}
        foreach ($dateField in @('timestamp_utc', 'started_at_utc')) {
            $parsedDate = [DateTimeOffset]::MinValue
            if (-not [DateTimeOffset]::TryParse(
                [string]$row.$dateField,
                [System.Globalization.CultureInfo]::InvariantCulture,
                [System.Globalization.DateTimeStyles]::AssumeUniversal -bor [System.Globalization.DateTimeStyles]::AdjustToUniversal,
                [ref]$parsedDate
            )) {
                throw "PhoBERT telemetry row $rowIndex has invalid $dateField"
            }
            $parsedDates[$dateField] = $parsedDate
        }
        $parsed = [ordered]@{}
        foreach ($numericField in $numericFields) {
            $number = 0.0
            if (-not [double]::TryParse(
                [string]$row.$numericField,
                [System.Globalization.NumberStyles]::Float,
                [System.Globalization.CultureInfo]::InvariantCulture,
                [ref]$number
            ) -or [double]::IsNaN($number) -or [double]::IsInfinity($number) -or $number -lt 0) {
                throw "PhoBERT telemetry row $rowIndex has invalid $numericField"
            }
            $parsed[$numericField] = $number
        }
        $pythonPidText = [string]$row.python_pid
        if ($pythonPidText -notmatch '^$|^[0-9]+(?:;[0-9]+)*$') {
            throw "PhoBERT telemetry row $rowIndex has invalid python_pid syntax"
        }
        if (-not [string]::IsNullOrEmpty($pythonPidText)) {
            $pythonPidNonemptySampleCount++
            $rowPids = [System.Collections.Generic.HashSet[long]]::new()
            foreach ($pythonPidToken in $pythonPidText.Split(';')) {
                $pythonPid = 0L
                if (-not [long]::TryParse(
                    $pythonPidToken,
                    [System.Globalization.NumberStyles]::None,
                    [System.Globalization.CultureInfo]::InvariantCulture,
                    [ref]$pythonPid
                ) -or $pythonPid -lt 0 -or $pythonPid -gt [int]::MaxValue) {
                    throw "PhoBERT telemetry row $rowIndex has an invalid python_pid value"
                }
                if (-not $rowPids.Add($pythonPid)) {
                    throw "PhoBERT telemetry row $rowIndex repeats python_pid=$pythonPid"
                }
                [void]$observedPythonPids.Add($pythonPid)
            }
        }
        if ($parsed.elapsed_seconds -lt $previousElapsed) {
            throw "PhoBERT telemetry elapsed_seconds regressed at row $rowIndex"
        }
        if ($rowIndex -eq 0) {
            $canonicalStartedAt = $parsedDates.started_at_utc
        }
        elseif ($parsedDates.started_at_utc -ne $canonicalStartedAt) {
            throw "PhoBERT telemetry started_at_utc changed at row $rowIndex"
        }
        if ($parsedDates.timestamp_utc -lt $parsedDates.started_at_utc) {
            throw "PhoBERT telemetry timestamp precedes sampler start at row $rowIndex"
        }
        $expectedElapsedSeconds = (
            $parsedDates.timestamp_utc - $parsedDates.started_at_utc
        ).TotalSeconds
        $elapsedDeltaSeconds = [math]::Abs(
            $parsed.elapsed_seconds - $expectedElapsedSeconds
        )
        if ($elapsedDeltaSeconds -gt $telemetryElapsedToleranceSeconds) {
            throw "PhoBERT telemetry elapsed_seconds differs from timestamp-started_at at row ${rowIndex}: delta_seconds=$elapsedDeltaSeconds"
        }
        $maximumObservedElapsedDeltaSeconds = [math]::Max(
            $maximumObservedElapsedDeltaSeconds,
            $elapsedDeltaSeconds
        )
        if ($rowIndex -gt 0) {
            $adjacentGapSeconds = (
                $parsedDates.timestamp_utc - $previousTimestamp
            ).TotalSeconds
            if ($adjacentGapSeconds -le 0) {
                throw "PhoBERT telemetry timestamp did not advance at row $rowIndex"
            }
            if ($adjacentGapSeconds -gt $telemetryMaxAdjacentGapSeconds) {
                throw "PhoBERT telemetry sampling gap exceeded limit at row ${rowIndex}: gap_seconds=$adjacentGapSeconds"
            }
            $maximumObservedAdjacentGapSeconds = [math]::Max(
                $maximumObservedAdjacentGapSeconds,
                $adjacentGapSeconds
            )
        }
        $previousElapsed = $parsed.elapsed_seconds
        $previousTimestamp = $parsedDates.timestamp_utc
        $parsedTimestamps.Add($parsedDates.timestamp_utc)
        $numericRows.Add([pscustomobject]$parsed)
    }

    $samplerStartDelaySeconds = (
        $canonicalStartedAt - $telemetryProcessStartedAt
    ).TotalSeconds
    if ($samplerStartDelaySeconds -lt -$telemetryClockSkewToleranceSeconds -or
        $samplerStartDelaySeconds -gt $telemetryStartedAtToleranceSeconds) {
        throw "PhoBERT telemetry started_at is not bound to wrapper creation: delay_seconds=$samplerStartDelaySeconds"
    }
    $firstSampleDelaySeconds = (
        $parsedTimestamps[0] - $telemetryProcessStartedAt
    ).TotalSeconds
    if ($firstSampleDelaySeconds -lt -$telemetryClockSkewToleranceSeconds -or
        $firstSampleDelaySeconds -gt $telemetryFirstSampleToleranceSeconds) {
        throw "PhoBERT telemetry first sample is outside startup tolerance: delay_seconds=$firstSampleDelaySeconds"
    }
    if ($Status -eq 'complete' -and $pythonPidNonemptySampleCount -eq 0) {
        throw 'Completed PhoBERT telemetry contains no sample with an observed Python PID'
    }

    $stopRequestedAt = [DateTimeOffset]::MinValue
    if (-not [DateTimeOffset]::TryParse(
        [string]$StopReceipt.telemetry_stop_requested_at_utc,
        [System.Globalization.CultureInfo]::InvariantCulture,
        [System.Globalization.DateTimeStyles]::AssumeUniversal -bor [System.Globalization.DateTimeStyles]::AdjustToUniversal,
        [ref]$stopRequestedAt
    )) {
        throw 'PhoBERT telemetry stop receipt has an invalid requested timestamp'
    }
    $finalSampleAgeSeconds = ($stopRequestedAt - $parsedTimestamps[-1]).TotalSeconds
    if ($finalSampleAgeSeconds -lt -$telemetryClockSkewToleranceSeconds -or
        $finalSampleAgeSeconds -gt $telemetryMaxAdjacentGapSeconds) {
        throw "PhoBERT telemetry final sample is stale or postdates stop: age_seconds=$finalSampleAgeSeconds"
    }

    $telemetrySha256 = Get-LowerSha256 -Path $telemetryPath
    $runEvidencePath = Join-Path $runRoot 'run-evidence.json'
    $payload = [ordered]@{
        schema_version = 'phase40-local-system-telemetry-v3'
        model_family = 'phobert'
        status = $Status
        detail = $Detail
        sealed_at_utc = [DateTime]::UtcNow.ToString('o')
        sample_count = $rows.Count
        first_sample_utc = if ($rows.Count) { $rows[0].timestamp_utc } else { $null }
        last_sample_utc = if ($rows.Count) { $rows[-1].timestamp_utc } else { $null }
        peak_vram_used_mib = (@($numericRows | ForEach-Object { $_.vram_used_mib }) | Measure-Object -Maximum).Maximum
        minimum_vram_free_mib = (@($numericRows | ForEach-Object { $_.vram_free_mib }) | Measure-Object -Minimum).Minimum
        peak_gpu_temperature_c = (@($numericRows | ForEach-Object { $_.gpu_temp_c }) | Measure-Object -Maximum).Maximum
        peak_gpu_power_w = (@($numericRows | ForEach-Object { $_.gpu_power_w }) | Measure-Object -Maximum).Maximum
        peak_python_rss_bytes = (@($numericRows | ForEach-Object { $_.python_rss_bytes }) | Measure-Object -Maximum).Maximum
        peak_system_ram_used_bytes = (@($numericRows | ForEach-Object { $_.system_ram_used_bytes }) | Measure-Object -Maximum).Maximum
        minimum_d_free_bytes = (@($numericRows | ForEach-Object { $_.d_free_bytes }) | Measure-Object -Minimum).Minimum
        telemetry_sha256 = $telemetrySha256
        telemetry_bytes = $telemetryItem.Length
        telemetry_pid = $StopReceipt.telemetry_pid
        telemetry_creation_utc_filetime_ticks = $StopReceipt.telemetry_creation_utc_filetime_ticks
        telemetry_exit_code = $StopReceipt.telemetry_exit_code
        telemetry_wrapper_sha256 = $StopReceipt.telemetry_wrapper_sha256
        telemetry_stderr_bytes = $StopReceipt.telemetry_stderr_bytes
        telemetry_stderr_sha256 = $StopReceipt.telemetry_stderr_sha256
        telemetry_stop_receipt_sha256 = $StopReceipt.telemetry_stop_receipt_sha256
        telemetry_stop_requested_at_utc = $StopReceipt.telemetry_stop_requested_at_utc
        final_sample_age_at_stop_seconds = $finalSampleAgeSeconds
        telemetry_process_started_at_utc = $telemetryProcessStartedAt.ToString('o')
        telemetry_sampler_started_at_utc = $canonicalStartedAt.ToString('o')
        sampler_start_delay_seconds = $samplerStartDelaySeconds
        first_sample_delay_seconds = $firstSampleDelaySeconds
        sampler_start_tolerance_seconds = $telemetryStartedAtToleranceSeconds
        first_sample_tolerance_seconds = $telemetryFirstSampleToleranceSeconds
        configured_sampler_interval_seconds = $telemetrySamplerIntervalSeconds
        maximum_allowed_adjacent_gap_seconds = $telemetryMaxAdjacentGapSeconds
        maximum_observed_adjacent_gap_seconds = $maximumObservedAdjacentGapSeconds
        elapsed_tolerance_seconds = $telemetryElapsedToleranceSeconds
        maximum_observed_elapsed_delta_seconds = $maximumObservedElapsedDeltaSeconds
        python_pid_nonempty_sample_count = $pythonPidNonemptySampleCount
        observed_python_pids = @($observedPythonPids | Sort-Object)
        continuous_coverage_verified = $true
        controller_pid = $controllerPid
        controller_creation_utc_filetime_ticks = $controllerCreationUtcFileTimeTicks
        controller_sha256 = $controllerSha256
        controller_lease_path = $controllerLeasePath
        controller_lease_held = $true
        request_sha256 = (Get-FileHash -LiteralPath $requestPath -Algorithm SHA256).Hash.ToLowerInvariant()
        base_manifest_sha256 = (Get-FileHash -LiteralPath $baseManifestPath -Algorithm SHA256).Hash.ToLowerInvariant()
        run_evidence_sha256 = if (Test-Path -LiteralPath $runEvidencePath -PathType Leaf) { (Get-FileHash -LiteralPath $runEvidencePath -Algorithm SHA256).Hash.ToLowerInvariant() } else { $null }
    }
    $payload | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath $summaryPath -Encoding utf8NoBOM
    if (-not (Test-Path -LiteralPath $summaryPath -PathType Leaf) -or
        (Get-Item -LiteralPath $summaryPath).Length -eq 0) {
        throw "PhoBERT telemetry summary write failed: $summaryPath"
    }
    $summarySha256 = Get-LowerSha256 -Path $summaryPath
    try {
        $readback = Get-Content -LiteralPath $summaryPath -Raw -Encoding utf8 -ErrorAction Stop |
            ConvertFrom-Json -ErrorAction Stop
    }
    catch {
        throw "PhoBERT telemetry summary readback failed: $($_.Exception.Message)"
    }
    if ($readback.schema_version -ne 'phase40-local-system-telemetry-v3' -or
        $readback.status -ne $Status -or
        [int]$readback.sample_count -ne $rows.Count -or
        $readback.telemetry_sha256 -ne $telemetrySha256 -or
        [int]$readback.telemetry_exit_code -ne 0 -or
        $readback.telemetry_process_started_at_utc -ne $telemetryProcessStartedAt.ToString('o') -or
        $readback.telemetry_sampler_started_at_utc -ne $canonicalStartedAt.ToString('o') -or
        [double]$readback.maximum_observed_adjacent_gap_seconds -gt $telemetryMaxAdjacentGapSeconds -or
        [double]$readback.maximum_observed_elapsed_delta_seconds -gt $telemetryElapsedToleranceSeconds -or
        ($Status -eq 'complete' -and [int]$readback.python_pid_nonempty_sample_count -le 0) -or
        $readback.continuous_coverage_verified -ne $true -or
        [long]$readback.controller_creation_utc_filetime_ticks -ne $controllerCreationUtcFileTimeTicks -or
        $readback.controller_sha256 -ne $controllerSha256 -or
        $readback.controller_lease_held -ne $true) {
        throw 'PhoBERT telemetry summary readback identity mismatch'
    }
    if ((Get-LowerSha256 -Path $summaryPath) -ne $summarySha256) {
        throw 'PhoBERT telemetry summary SHA-256 changed during verification'
    }
    $verificationPayload = [ordered]@{
        schema_version = 'phase40-local-system-telemetry-verification-v2'
        verified_at_utc = [DateTime]::UtcNow.ToString('o')
        status = $Status
        sample_count = $rows.Count
        telemetry_csv_path = $telemetryPath
        telemetry_csv_bytes = $telemetryItem.Length
        telemetry_csv_sha256 = $telemetrySha256
        telemetry_summary_path = $summaryPath
        telemetry_summary_sha256 = $summarySha256
        telemetry_process_exit_code = $StopReceipt.telemetry_exit_code
        telemetry_stderr_bytes = $StopReceipt.telemetry_stderr_bytes
        telemetry_process_started_at_utc = $telemetryProcessStartedAt.ToString('o')
        telemetry_sampler_started_at_utc = $canonicalStartedAt.ToString('o')
        sampler_start_delay_seconds = $samplerStartDelaySeconds
        first_sample_delay_seconds = $firstSampleDelaySeconds
        sampler_start_tolerance_seconds = $telemetryStartedAtToleranceSeconds
        first_sample_tolerance_seconds = $telemetryFirstSampleToleranceSeconds
        maximum_observed_adjacent_gap_seconds = $maximumObservedAdjacentGapSeconds
        maximum_observed_elapsed_delta_seconds = $maximumObservedElapsedDeltaSeconds
        python_pid_nonempty_sample_count = $pythonPidNonemptySampleCount
        continuous_coverage_verified = $true
        controller_pid = $controllerPid
        controller_creation_utc_filetime_ticks = $controllerCreationUtcFileTimeTicks
        controller_sha256 = $controllerSha256
        controller_lease_path = $controllerLeasePath
        controller_lease_held = $true
        summary_readback_verified = $true
        summary_hash_verified = $true
    }
    $verificationPayload | ConvertTo-Json -Depth 4 |
        Set-Content -LiteralPath $telemetryVerificationReceiptPath -Encoding utf8NoBOM
    try {
        $verificationReadback = Get-Content -LiteralPath $telemetryVerificationReceiptPath -Raw -Encoding utf8 -ErrorAction Stop |
            ConvertFrom-Json -ErrorAction Stop
    }
    catch {
        throw "PhoBERT telemetry verification receipt readback failed: $($_.Exception.Message)"
    }
    if ($verificationReadback.schema_version -ne 'phase40-local-system-telemetry-verification-v2' -or
        $verificationReadback.telemetry_summary_sha256 -ne $summarySha256 -or
        $verificationReadback.telemetry_csv_sha256 -ne $telemetrySha256 -or
        [int]$verificationReadback.sample_count -ne $rows.Count -or
        $verificationReadback.status -ne $Status -or
        [double]$verificationReadback.maximum_observed_adjacent_gap_seconds -gt $telemetryMaxAdjacentGapSeconds -or
        [double]$verificationReadback.maximum_observed_elapsed_delta_seconds -gt $telemetryElapsedToleranceSeconds -or
        ($Status -eq 'complete' -and [int]$verificationReadback.python_pid_nonempty_sample_count -le 0) -or
        $verificationReadback.continuous_coverage_verified -ne $true -or
        $verificationReadback.summary_readback_verified -ne $true -or
        $verificationReadback.summary_hash_verified -ne $true) {
        throw 'PhoBERT telemetry verification receipt identity mismatch'
    }
    $verificationReceiptSha256 = Get-LowerSha256 -Path $telemetryVerificationReceiptPath
    Write-ChainLog "verified PhoBERT telemetry status=$Status samples=$($rows.Count) csv_sha256=$telemetrySha256 summary_sha256=$summarySha256 receipt_sha256=$verificationReceiptSha256"
    return [pscustomobject]@{
        Status = $Status
        SampleCount = $rows.Count
        TelemetrySha256 = $telemetrySha256
        SummarySha256 = $summarySha256
        VerificationReceiptSha256 = $verificationReceiptSha256
    }
}

function Assert-FreshPhoBertTargets {
    foreach ($freshTarget in @(
        $workParent,
        $runRoot,
        $telemetryPath,
        $telemetryStdout,
        $telemetryStderr,
        $telemetryStopPath,
        $summaryPath,
        $telemetryVerificationReceiptPath
    )) {
        if (Test-Path -LiteralPath $freshTarget) {
            throw "Refusing non-fresh PhoBERT target: $freshTarget"
        }
    }
    Write-ChainLog 'verified fresh PhoBERT work, run, and telemetry targets'
}

$controllerLeaseStream = Open-ControllerLease
$terminalStatus = 'failed'
$terminalDetail = ''
$telemetryProcess = $null
$telemetryStopReceipt = $null
$telemetryEvidenceVerified = $false

try {
    Write-ChainLog "exclusive controller lease acquired path=$controllerLeasePath controller_sha256=$controllerSha256"
    foreach ($requiredPath in @(
        $sourceRuntime,
        $transferRoot,
        $requestPath,
        $sourceArchivePath,
        $sourceManifestPath,
        $inputArchive,
        $inputRoot,
        $baseModelPath,
        $baseManifestPath,
        $telemetryScript,
        $pythonExe,
        $pwshExe
    )) {
        if (-not (Test-Path -LiteralPath $requiredPath)) {
            throw "Required chain path is missing: $requiredPath"
        }
    }
    [void](Assert-FrozenSourceRuntime -Stage 'armed')
    Assert-FreshPhoBertTargets

    $qwenSupervisor = Get-Process -Id $QwenSupervisorPid -ErrorAction SilentlyContinue
    $qwenStartTicks = if ($null -ne $qwenSupervisor) {
        $qwenSupervisor.StartTime.ToUniversalTime().Ticks
    }
    else {
        $null
    }
    $qwenTrainer = Get-Process -Id $QwenTrainerPid -ErrorAction SilentlyContinue
    $qwenTrainerStartTicks = if ($null -ne $qwenTrainer) {
        $qwenTrainer.StartTime.ToUniversalTime().Ticks
    }
    else {
        0
    }
    Write-ChainLog "armed after qwen_supervisor_pid=$QwenSupervisorPid"
    while ($true) {
        $live = Get-Process -Id $QwenSupervisorPid -ErrorAction SilentlyContinue
        if ($null -eq $live) {
            break
        }
        if ($null -ne $qwenStartTicks -and $live.StartTime.ToUniversalTime().Ticks -ne $qwenStartTicks) {
            break
        }
        Start-Sleep -Seconds 60
    }
    Start-Sleep -Seconds 5
    Write-ChainLog 'Qwen supervisor exited; verifying Qwen evidence and GGUF'
    Assert-QwenCompletion
    Wait-QwenGpuRelease -TrainerStartTicks $qwenTrainerStartTicks
    [void](Assert-FrozenSourceRuntime -Stage 'prelaunch')
    Assert-FreshPhoBertTargets

    if ((Invoke-PhoBertDoctor) -ne 0) {
        throw 'PhoBERT doctor failed after Qwen completion'
    }
    # The doctor is itself a Python process, so close its target-creation
    # window before creating any PhoBERT work or telemetry artifact.
    Assert-FreshPhoBertTargets
    New-Item -ItemType Directory -Path $workParent | Out-Null
    $telemetryProcess = Start-PhoBertTelemetry
    Start-Sleep -Seconds 3
    if (-not (Get-Process -Id $telemetryProcess.Id -ErrorAction SilentlyContinue)) {
        throw 'PhoBERT telemetry process stopped during startup'
    }
    Write-ChainLog "started PhoBERT telemetry pid=$($telemetryProcess.Id)"

    $freshExit = Invoke-PhoBertTraining
    Write-ChainLog "PhoBERT fresh training exit=$freshExit"
    if ($freshExit -ne 0) {
        throw "PhoBERT fresh training exited nonzero: $freshExit"
    }
    $complete = Test-PhoBertRunComplete
    for ($attempt = 1; -not $complete -and $attempt -le $MaxResumeAttempts; $attempt++) {
        $checkpoint = Get-LatestPhoBertCheckpoint
        if ($null -eq $checkpoint) {
            throw 'PhoBERT stopped without complete evidence or an exact sealed checkpoint'
        }
        [void](Invoke-VerifiedPhoBertResume -Checkpoint $checkpoint -Attempt $attempt)
        $complete = Test-PhoBertRunComplete
    }
    if (-not $complete) {
        throw 'PhoBERT fresh training did not produce complete evidence; automated resume is disabled because the frozen v3 local-Windows resume path is invalid'
    }
    if ((Invoke-PhoBertRenderGraphs) -ne 0) {
        throw 'PhoBERT graph rendering failed after complete training'
    }
    if (-not (Test-PhoBertRunComplete)) {
        throw 'PhoBERT run evidence failed verification after graph rendering'
    }

    $terminalStatus = 'complete'
    $terminalDetail = 'Qwen evidence/GGUF verified; full local PhoBERT evidence verified.'
    Write-ChainLog $terminalDetail
}
catch {
    $terminalDetail = $_.Exception.Message
    Write-ChainLog "terminal failure: $terminalDetail"
}
finally {
    if ($null -ne $telemetryProcess) {
        try {
            $telemetryStopReceipt = Stop-PhoBertTelemetry -TelemetryProcess $telemetryProcess
        }
        catch {
            $telemetryFailure = "PhoBERT telemetry controlled-stop failure: $($_.Exception.Message)"
            $terminalStatus = 'failed'
            $terminalDetail = if ([string]::IsNullOrWhiteSpace($terminalDetail)) {
                $telemetryFailure
            }
            else {
                "$terminalDetail | $telemetryFailure"
            }
            Write-ChainLog "terminal failure: $telemetryFailure"
        }
    }
    elseif ($terminalStatus -eq 'complete') {
        $telemetryFailure = 'PhoBERT model evidence completed without a telemetry process'
        $terminalStatus = 'failed'
        $terminalDetail = "$terminalDetail | $telemetryFailure"
        Write-ChainLog "terminal failure: $telemetryFailure"
    }

    if ($null -ne $telemetryStopReceipt) {
        try {
            $telemetrySeal = Write-PhoBertTelemetrySeal `
                -Status $terminalStatus `
                -Detail $terminalDetail `
                -StopReceipt $telemetryStopReceipt
            if ($telemetrySeal.Status -ne $terminalStatus -or $telemetrySeal.SampleCount -le 0) {
                throw 'PhoBERT telemetry seal returned an invalid verification result'
            }
            $telemetryEvidenceVerified = $true
        }
        catch {
            $telemetryFailure = "PhoBERT telemetry seal verification failure: $($_.Exception.Message)"
            $terminalStatus = 'failed'
            $terminalDetail = if ([string]::IsNullOrWhiteSpace($terminalDetail)) {
                $telemetryFailure
            }
            else {
                "$terminalDetail | $telemetryFailure"
            }
            Write-ChainLog "terminal failure: $telemetryFailure"
        }
    }
    if ($terminalStatus -eq 'complete' -and -not $telemetryEvidenceVerified) {
        $telemetryFailure = 'PhoBERT model evidence completed without a verified telemetry summary'
        $terminalStatus = 'failed'
        $terminalDetail = "$terminalDetail | $telemetryFailure"
        Write-ChainLog "terminal failure: $telemetryFailure"
    }
    if ($null -ne $controllerLeaseStream) {
        try {
            Write-ChainLog "releasing exclusive controller lease path=$controllerLeasePath terminal_status=$terminalStatus"
        }
        finally {
            $controllerLeaseStream.Dispose()
            $controllerLeaseStream = $null
        }
    }
}

if ($terminalStatus -ne 'complete') {
    exit 1
}
exit 0
