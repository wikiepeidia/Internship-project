Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$preflightScript = Join-Path $PSScriptRoot 'comparison-authority-preflight.ps1'
$pwshExe = Join-Path $PSHOME 'pwsh.exe'
$testRoot = Join-Path ([System.IO.Path]::GetTempPath()) (
    'phase40-comparison-preflight-' + [Guid]::NewGuid().ToString('N')
)

function Assert-True {
    param([Parameter(Mandatory)][bool]$Condition, [Parameter(Mandatory)][string]$Message)
    if (-not $Condition) {
        throw $Message
    }
}

function Get-LowerSha256 {
    param([Parameter(Mandatory)][string]$Path)
    return (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLowerInvariant()
}

function Get-TreeSha256 {
    param([Parameter(Mandatory)][object[]]$Entries)
    $inventoryJson = ConvertTo-Json -InputObject $Entries -Depth 4 -Compress
    $inventoryBytes = [System.Text.UTF8Encoding]::new($false).GetBytes(
        $inventoryJson + "`n"
    )
    $prefix = [System.Text.UTF8Encoding]::new($false).GetBytes(
        "phase40-comparison-finalizer-source-v1`0"
    )
    $combined = [byte[]]::new($prefix.Length + $inventoryBytes.Length)
    [System.Buffer]::BlockCopy($prefix, 0, $combined, 0, $prefix.Length)
    [System.Buffer]::BlockCopy(
        $inventoryBytes,
        0,
        $combined,
        $prefix.Length,
        $inventoryBytes.Length
    )
    return [System.Convert]::ToHexString(
        [System.Security.Cryptography.SHA256]::HashData($combined)
    ).ToLowerInvariant()
}

function New-Fixture {
    param(
        [Parameter(Mandatory)][string]$Name,
        [switch]$DuplicatePath,
        [switch]$JunctionSource
    )
    $root = Join-Path $testRoot $Name
    [void](New-Item -ItemType Directory -Path $root)
    $sourceRoot = Join-Path $root 'src'
    if ($JunctionSource) {
        $junctionTarget = Join-Path $testRoot ($Name + '-junction-target')
        [void](New-Item -ItemType Directory -Path $junctionTarget)
        [void](New-Item -ItemType Junction -Path $sourceRoot -Target $junctionTarget)
    }
    else {
        [void](New-Item -ItemType Directory -Path $sourceRoot)
    }

    $first = Join-Path $sourceRoot 'a.py'
    $second = Join-Path $sourceRoot 'b.py'
    [System.IO.File]::WriteAllText(
        $first,
        "A = 1`n",
        [System.Text.UTF8Encoding]::new($false)
    )
    [System.IO.File]::WriteAllText(
        $second,
        "B = 2`n",
        [System.Text.UTF8Encoding]::new($false)
    )
    $entries = [System.Collections.Generic.List[object]]::new()
    $entries.Add([ordered]@{
        bytes = (Get-Item -LiteralPath $first).Length
        path = 'src/a.py'
        sha256 = Get-LowerSha256 -Path $first
    })
    $entries.Add([ordered]@{
        bytes = (Get-Item -LiteralPath $second).Length
        path = 'src/b.py'
        sha256 = Get-LowerSha256 -Path $second
    })
    if ($DuplicatePath) {
        $entries.Add([ordered]@{
            bytes = (Get-Item -LiteralPath $first).Length
            path = 'src/a.py'
            sha256 = Get-LowerSha256 -Path $first
        })
    }

    $requestPath = Join-Path $root 'request.json'
    [System.IO.File]::WriteAllText(
        $requestPath,
        "{`"fixture`":true}`n",
        [System.Text.UTF8Encoding]::new($false)
    )
    $requestSha = Get-LowerSha256 -Path $requestPath
    $entryArray = [object[]]$entries.ToArray()
    $amendment = [ordered]@{
        schema_version = 'phase40-two-full-model-scope-amendment-v1'
        original_run_request_sha256 = $requestSha
        comparison_finalizer_authority = [ordered]@{
            schema_version = 'phase40-comparison-finalizer-authority-v1'
            source_tree_sha256 = Get-TreeSha256 -Entries $entryArray
            files = $entryArray
        }
    }
    $amendmentPath = Join-Path $root 'amendment.json'
    [System.IO.File]::WriteAllText(
        $amendmentPath,
        (($amendment | ConvertTo-Json -Depth 8) + "`n"),
        [System.Text.UTF8Encoding]::new($false)
    )
    return [pscustomobject]@{
        Root = $root
        Amendment = $amendmentPath
        Request = $requestPath
        FirstSource = $first
        Receipt = Join-Path $root 'receipt.json'
    }
}

function Invoke-Preflight {
    param([Parameter(Mandatory)]$Fixture)
    $output = & $pwshExe -NoLogo -NoProfile -NonInteractive `
        -File $preflightScript `
        -RepoRoot $Fixture.Root `
        -AmendmentPath 'amendment.json' `
        -RequestPath 'request.json' `
        -OutputPath 'receipt.json' 2>&1
    return [pscustomobject]@{
        ExitCode = $LASTEXITCODE
        Output = ($output -join "`n")
    }
}

try {
    [void](New-Item -ItemType Directory -Path $testRoot)

    $valid = New-Fixture -Name 'valid'
    $validResult = Invoke-Preflight -Fixture $valid
    Assert-True ($validResult.ExitCode -eq 0) "valid fixture failed: $($validResult.Output)"
    $receipt = Get-Content -LiteralPath $valid.Receipt -Raw -Encoding utf8 | ConvertFrom-Json
    Assert-True (
        $receipt.preflight_script_sha256 -eq (Get-LowerSha256 -Path $preflightScript)
    ) 'receipt does not bind the exact preflight script'

    $tampered = New-Fixture -Name 'tampered-source'
    [System.IO.File]::AppendAllText(
        $tampered.FirstSource,
        "# drift`n",
        [System.Text.UTF8Encoding]::new($false)
    )
    $tamperedResult = Invoke-Preflight -Fixture $tampered
    Assert-True ($tamperedResult.ExitCode -ne 0) 'tampered source unexpectedly passed'
    Assert-True (-not (Test-Path -LiteralPath $tampered.Receipt)) 'tamper wrote a receipt'

    $duplicatePath = New-Fixture -Name 'duplicate-path' -DuplicatePath
    $duplicatePathResult = Invoke-Preflight -Fixture $duplicatePath
    Assert-True ($duplicatePathResult.ExitCode -ne 0) 'duplicate authority path passed'

    $duplicateJson = New-Fixture -Name 'duplicate-json-key'
    $jsonText = [System.IO.File]::ReadAllText($duplicateJson.Amendment)
    $needle = '"schema_version": "phase40-two-full-model-scope-amendment-v1",'
    $replacement = $needle + "`n  " + $needle
    $jsonText = $jsonText.Replace($needle, $replacement)
    [System.IO.File]::WriteAllText(
        $duplicateJson.Amendment,
        $jsonText,
        [System.Text.UTF8Encoding]::new($false)
    )
    $duplicateJsonResult = Invoke-Preflight -Fixture $duplicateJson
    Assert-True ($duplicateJsonResult.ExitCode -ne 0) 'duplicate JSON key passed'

    $junction = New-Fixture -Name 'junction-source' -JunctionSource
    $junctionResult = Invoke-Preflight -Fixture $junction
    Assert-True ($junctionResult.ExitCode -ne 0) 'reparse-point source passed'

    $existing = New-Fixture -Name 'existing-output'
    $sentinel = [System.Text.UTF8Encoding]::new($false).GetBytes("do-not-overwrite`n")
    [System.IO.File]::WriteAllBytes($existing.Receipt, $sentinel)
    $existingResult = Invoke-Preflight -Fixture $existing
    Assert-True ($existingResult.ExitCode -ne 0) 'existing output unexpectedly passed'
    Assert-True (
        [System.Linq.Enumerable]::SequenceEqual(
            [byte[]]$sentinel,
            [byte[]][System.IO.File]::ReadAllBytes($existing.Receipt)
        )
    ) 'existing output was modified'

    $concurrent = New-Fixture -Name 'concurrent-output'
    $argumentString = "-NoLogo -NoProfile -NonInteractive -File `"$preflightScript`" -RepoRoot `"$($concurrent.Root)`" -AmendmentPath amendment.json -RequestPath request.json -OutputPath receipt.json"
    $oneOut = Join-Path $concurrent.Root 'one.stdout.log'
    $oneErr = Join-Path $concurrent.Root 'one.stderr.log'
    $twoOut = Join-Path $concurrent.Root 'two.stdout.log'
    $twoErr = Join-Path $concurrent.Root 'two.stderr.log'
    $one = Start-Process -FilePath $pwshExe -ArgumentList $argumentString `
        -WindowStyle Hidden -RedirectStandardOutput $oneOut -RedirectStandardError $oneErr `
        -PassThru
    $two = Start-Process -FilePath $pwshExe -ArgumentList $argumentString `
        -WindowStyle Hidden -RedirectStandardOutput $twoOut -RedirectStandardError $twoErr `
        -PassThru
    $one.WaitForExit()
    $two.WaitForExit()
    $exitCodes = @($one.ExitCode, $two.ExitCode)
    Assert-True (
        (@($exitCodes | Where-Object { $_ -eq 0 }).Count -eq 1) -and
        (@($exitCodes | Where-Object { $_ -ne 0 }).Count -eq 1)
    ) "concurrent writers were not exactly one PASS/one BLOCK: $($exitCodes -join ',')"
    Assert-True (Test-Path -LiteralPath $concurrent.Receipt -PathType Leaf) `
        'concurrent PASS did not create one receipt'

    Write-Output 'PASS comparison-authority preflight synthetic tests=7'
}
finally {
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
