[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$repo = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\..\..'))
$fixturePath = Join-Path $repo 'tests\architecture\fixtures\protected_authority_baseline.json'
$gitCommand = Get-Command git -CommandType Application -ErrorAction Stop
$gitExe = [System.IO.Path]::GetFullPath($gitCommand.Source)
if (-not [System.IO.Path]::IsPathRooted($gitExe) -or -not [System.IO.File]::Exists($gitExe)) {
    throw 'git executable must resolve to one existing absolute application path'
}

$forbiddenGitEnvironment = @(
    'GIT_DIR', 'GIT_WORK_TREE', 'GIT_COMMON_DIR', 'GIT_INDEX_FILE',
    'GIT_OBJECT_DIRECTORY', 'GIT_ALTERNATE_OBJECT_DIRECTORIES',
    'GIT_QUARANTINE_PATH', 'GIT_NAMESPACE'
)
foreach ($name in $forbiddenGitEnvironment) {
    if ([Environment]::GetEnvironmentVariable($name)) {
        throw "forbidden Git environment variable is set: $name"
    }
}
$alternatesPath = Join-Path $repo '.git\objects\info\alternates'
if ([System.IO.File]::Exists($alternatesPath)) {
    throw 'Git object alternates are forbidden'
}

$raw = [System.IO.File]::ReadAllText($fixturePath, [System.Text.UTF8Encoding]::new($false, $true))
$document = [System.Text.Json.JsonDocument]::Parse($raw)
try {
    $root = $document.RootElement
    if ($root.ValueKind -ne [System.Text.Json.JsonValueKind]::Object) {
        throw 'authority fixture root must be an object'
    }
    function Assert-ExactProperties {
        param([System.Text.Json.JsonElement]$Element, [string[]]$Expected, [string]$Where)
        $actual = @($Element.EnumerateObject() | ForEach-Object { $_.Name })
        if (@($actual | Sort-Object -Unique).Count -ne $actual.Count) {
            throw "duplicate property in $Where"
        }
        if (($actual -join "`n") -ne ($Expected -join "`n")) {
            throw "schema or property-order drift in $Where"
        }
    }
    Assert-ExactProperties $root @(
        'archive_publication_commit', 'baseline_commit', 'expected_member_count',
        'historical_mirror', 'protected_authorities', 'receipt_bytes', 'schema_version'
    ) 'authority fixture'
    $publicationCommit = $root.GetProperty('archive_publication_commit').GetString()
    if ($publicationCommit -cne 'b0d24820720f53100d9a94174790d70b5354fa27') {
        throw 'archive publication commit drift'
    }
    if ($root.GetProperty('expected_member_count').GetInt32() -ne 40) {
        throw 'expected member count drift'
    }
    if ($root.GetProperty('receipt_bytes').GetInt32() -ne 1746) {
        throw 'receipt byte count drift'
    }
    $mirror = $root.GetProperty('historical_mirror')
    Assert-ExactProperties $mirror @(
        'destination', 'launcher', 'manifest_schema_version', 'source_tree_sha256', 'sources'
    ) 'historical mirror'
    $destination = $mirror.GetProperty('destination').GetString()
    $members = [System.Collections.Generic.List[object]]::new()
    $members.Add([pscustomobject]@{ Path = "$destination/execution-source-manifest.json"; Bytes = 6324 })
    $members.Add([pscustomobject]@{ Path = "$destination/archival-receipt.json"; Bytes = 1746 })
    $sources = @($mirror.GetProperty('sources').EnumerateArray())
    if ($sources.Count -ne 37) { throw 'historical source member count drift' }
    foreach ($source in $sources) {
        Assert-ExactProperties $source @('bytes', 'path', 'sha256') 'historical source member'
        $members.Add([pscustomobject]@{
            Path = "$destination/tree/$($source.GetProperty('path').GetString())"
            Bytes = $source.GetProperty('bytes').GetInt64()
        })
    }
    $launcher = $mirror.GetProperty('launcher')
    Assert-ExactProperties $launcher @('bytes', 'path', 'sha256') 'historical launcher'
    $members.Add([pscustomobject]@{
        Path = "$destination/tree/$($launcher.GetProperty('path').GetString())"
        Bytes = $launcher.GetProperty('bytes').GetInt64()
    })
    if ($members.Count -ne 40) { throw 'derived member count must equal exactly 40' }
    $paths = @($members | ForEach-Object { $_.Path })
    if (@($paths | Sort-Object -Unique).Count -ne 40) { throw 'duplicate archive member path' }
    foreach ($path in $paths) {
        if ($path.Contains('\') -or $path.StartsWith('/') -or $path -match '^[A-Za-z]:' -or
            $path -match '(^|/)\.\.(/|$)' -or $path -match '(^|/)\.(/|$)' -or
            $path.Contains('//')) {
            throw "unsafe or separator-drifted archive member path: $path"
        }
    }

    $env:GIT_OPTIONAL_LOCKS = '0'
    $oldLocation = Get-Location
    try {
        Set-Location -LiteralPath $repo
        if ([System.IO.Path]::GetFullPath((Get-Location).Path) -cne $repo) {
            throw 'Git verifier current directory is not the exact repository root'
        }
        $replaceOutput = & $gitExe --no-replace-objects -C $repo --literal-pathspecs config --local --get-regexp '^replace\.' 2>&1
        if ($LASTEXITCODE -eq 0 -and @($replaceOutput).Count -gt 0) {
            throw 'Git replacement-object configuration is forbidden'
        }
        if ($LASTEXITCODE -notin @(0, 1)) { throw 'Git replacement-object configuration check failed' }

        foreach ($member in $members) {
            $path = [string]$member.Path
            $stageOutput = @(& $gitExe --no-replace-objects -C $repo --literal-pathspecs ls-files --stage -- $path 2>&1)
            if ($LASTEXITCODE -ne 0 -or $stageOutput.Count -ne 1) {
                throw "expected exactly one index record for $path"
            }
            $match = [regex]::Match([string]$stageOutput[0], '^100644 ([0-9a-f]{40,64}) 0\t(.+)$')
            if (-not $match.Success -or $match.Groups[2].Value -cne $path) {
                throw "index mode, stage, or literal path drift for $path"
            }
            $indexOid = $match.Groups[1].Value
            $commitOid = @(& $gitExe --no-replace-objects -C $repo --literal-pathspecs rev-parse "$publicationCommit`:$path" 2>&1)
            if ($LASTEXITCODE -ne 0 -or $commitOid.Count -ne 1 -or [string]$commitOid[0] -cne $indexOid) {
                throw "index/publication object mismatch for $path"
            }
            $objectType = @(& $gitExe --no-replace-objects -C $repo --literal-pathspecs cat-file -t $indexOid 2>&1)
            if ($LASTEXITCODE -ne 0 -or $objectType.Count -ne 1 -or [string]$objectType[0] -cne 'blob') {
                throw "non-blob archive object for $path"
            }
            $objectSize = @(& $gitExe --no-replace-objects -C $repo --literal-pathspecs cat-file -s $indexOid 2>&1)
            if ($LASTEXITCODE -ne 0 -or $objectSize.Count -ne 1 -or [int64]$objectSize[0] -ne [int64]$member.Bytes) {
                throw "reviewed byte-size mismatch for $path"
            }
        }
    }
    finally {
        Set-Location -LiteralPath $oldLocation
    }
    Write-Output 'verified 40 archived source members by immutable Git metadata'
}
finally {
    $document.Dispose()
}
