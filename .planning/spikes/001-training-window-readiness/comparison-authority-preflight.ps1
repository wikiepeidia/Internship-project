param(
    [string]$RepoRoot = '.',
    [string]$AmendmentPath = 'data/models/phase40/two-full-model-scope-amendment.json',
    [string]$RequestPath = 'data/models/phase40/full-run-request.json',
    [string]$OutputPath = 'data/models/phase40/comparison-authority-preflight.json'
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Get-LowerSha256 {
    param([Parameter(Mandatory)][string]$Path)
    return (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLowerInvariant()
}

function Assert-ContainedRegularPath {
    param(
        [Parameter(Mandatory)][string]$Root,
        [Parameter(Mandatory)][string]$Path,
        [switch]$AllowMissingLeaf
    )
    $rootFull = [System.IO.Path]::GetFullPath($Root).TrimEnd(
        [System.IO.Path]::DirectorySeparatorChar
    )
    $pathFull = [System.IO.Path]::GetFullPath($Path)
    $prefix = $rootFull + [System.IO.Path]::DirectorySeparatorChar
    if (-not $pathFull.StartsWith($prefix, [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "Authority path escaped repository root: $pathFull"
    }
    $current = if ($AllowMissingLeaf -and -not (Test-Path -LiteralPath $pathFull)) {
        [System.IO.Path]::GetDirectoryName($pathFull)
    }
    else {
        $pathFull
    }
    while ($true) {
        $item = Get-Item -LiteralPath $current -Force
        if ($item.Attributes -band [System.IO.FileAttributes]::ReparsePoint) {
            throw "Authority path contains a reparse point: $current"
        }
        if ($current.Equals($rootFull, [System.StringComparison]::OrdinalIgnoreCase)) {
            break
        }
        $parent = [System.IO.Path]::GetDirectoryName($current)
        if (-not $parent -or $parent.Equals($current, [System.StringComparison]::OrdinalIgnoreCase)) {
            throw "Authority path did not reach repository root: $pathFull"
        }
        $current = $parent
    }
    if (-not $AllowMissingLeaf) {
        $leaf = Get-Item -LiteralPath $pathFull -Force
        if ($leaf.PSIsContainer -or
            ($leaf.Attributes -band [System.IO.FileAttributes]::ReparsePoint)) {
            throw "Authority source is not one regular file: $pathFull"
        }
    }
    return $pathFull
}

function Get-CombinedSha256 {
    param(
        [Parameter(Mandatory)][byte[]]$Prefix,
        [Parameter(Mandatory)][byte[]]$Payload
    )
    $combined = [byte[]]::new($Prefix.Length + $Payload.Length)
    [System.Buffer]::BlockCopy($Prefix, 0, $combined, 0, $Prefix.Length)
    [System.Buffer]::BlockCopy($Payload, 0, $combined, $Prefix.Length, $Payload.Length)
    return [System.Convert]::ToHexString(
        [System.Security.Cryptography.SHA256]::HashData($combined)
    ).ToLowerInvariant()
}

function Assert-NoDuplicateJsonProperties {
    param(
        [Parameter(Mandatory)][System.Text.Json.JsonElement]$Element,
        [string]$Context = '$'
    )
    if ($Element.ValueKind -eq [System.Text.Json.JsonValueKind]::Object) {
        $names = [System.Collections.Generic.HashSet[string]]::new(
            [System.StringComparer]::Ordinal
        )
        foreach ($property in $Element.EnumerateObject()) {
            if (-not $names.Add($property.Name)) {
                throw "Duplicate JSON property at ${Context}: $($property.Name)"
            }
            Assert-NoDuplicateJsonProperties `
                -Element $property.Value `
                -Context "${Context}.$($property.Name)"
        }
    }
    elseif ($Element.ValueKind -eq [System.Text.Json.JsonValueKind]::Array) {
        $index = 0
        foreach ($item in $Element.EnumerateArray()) {
            Assert-NoDuplicateJsonProperties -Element $item -Context "${Context}[$index]"
            $index++
        }
    }
}

function ConvertFrom-StrictJsonBytes {
    param(
        [Parameter(Mandatory)][byte[]]$Payload,
        [Parameter(Mandatory)][string]$Description
    )
    try {
        $text = [System.Text.UTF8Encoding]::new($false, $true).GetString($Payload)
        $options = [System.Text.Json.JsonDocumentOptions]::new()
        $options.AllowTrailingCommas = $false
        $options.CommentHandling = [System.Text.Json.JsonCommentHandling]::Disallow
        $document = [System.Text.Json.JsonDocument]::Parse($text, $options)
    }
    catch {
        throw "$Description is not strict UTF-8 JSON: $($_.Exception.Message)"
    }
    try {
        if ($document.RootElement.ValueKind -ne [System.Text.Json.JsonValueKind]::Object) {
            throw "$Description must be one JSON object"
        }
        Assert-NoDuplicateJsonProperties -Element $document.RootElement
    }
    finally {
        $document.Dispose()
    }
    return $text | ConvertFrom-Json
}

function Write-ExclusiveUtf8 {
    param(
        [Parameter(Mandatory)][string]$Path,
        [Parameter(Mandatory)][string]$Text
    )
    $payload = [System.Text.UTF8Encoding]::new($false).GetBytes($Text)
    try {
        $stream = [System.IO.FileStream]::new(
            $Path,
            [System.IO.FileMode]::CreateNew,
            [System.IO.FileAccess]::Write,
            [System.IO.FileShare]::None,
            4096,
            [System.IO.FileOptions]::WriteThrough
        )
    }
    catch [System.IO.IOException] {
        throw "Refusing to overwrite or race a frozen preflight receipt: $Path"
    }
    try {
        $stream.Write($payload, 0, $payload.Length)
        $stream.Flush($true)
    }
    finally {
        $stream.Dispose()
    }
}

$repoFull = [System.IO.Path]::GetFullPath($RepoRoot)
if (-not (Test-Path -LiteralPath $repoFull -PathType Container)) {
    throw "Repository root is missing: $repoFull"
}
$repoItem = Get-Item -LiteralPath $repoFull -Force
if ($repoItem.Attributes -band [System.IO.FileAttributes]::ReparsePoint) {
    throw "Repository root cannot be a reparse point: $repoFull"
}

$amendmentFull = Assert-ContainedRegularPath -Root $repoFull -Path (
    Join-Path $repoFull $AmendmentPath
)
$requestFull = Assert-ContainedRegularPath -Root $repoFull -Path (
    Join-Path $repoFull $RequestPath
)
$outputFull = Assert-ContainedRegularPath -Root $repoFull -Path (
    Join-Path $repoFull $OutputPath
) -AllowMissingLeaf
if (Test-Path -LiteralPath $outputFull) {
    throw "Refusing to overwrite frozen preflight receipt: $outputFull"
}

$amendmentBytes = [System.IO.File]::ReadAllBytes($amendmentFull)
$requestBytes = [System.IO.File]::ReadAllBytes($requestFull)
$amendmentSha256 = [System.Convert]::ToHexString(
    [System.Security.Cryptography.SHA256]::HashData($amendmentBytes)
).ToLowerInvariant()
$requestSha256 = [System.Convert]::ToHexString(
    [System.Security.Cryptography.SHA256]::HashData($requestBytes)
).ToLowerInvariant()
$amendment = ConvertFrom-StrictJsonBytes `
    -Payload $amendmentBytes `
    -Description 'Scope amendment'
if ($amendment.schema_version -ne 'phase40-two-full-model-scope-amendment-v1') {
    throw 'Scope amendment schema is not recognized'
}
if ($amendment.original_run_request_sha256 -ne $requestSha256) {
    throw 'Scope amendment does not bind the exact frozen run request'
}
$authority = $amendment.comparison_finalizer_authority
if ($authority.schema_version -ne 'phase40-comparison-finalizer-authority-v1') {
    throw 'Comparison-finalizer authority schema is not recognized'
}

$verified = [System.Collections.Generic.List[object]]::new()
$seen = [System.Collections.Generic.HashSet[string]]::new(
    [System.StringComparer]::Ordinal
)
foreach ($entry in @($authority.files)) {
    $relative = [string]$entry.path
    if ([System.IO.Path]::IsPathRooted($relative) -or
        $relative.Split('/') -contains '..' -or
        -not $seen.Add($relative)) {
        throw "Unsafe or duplicate finalizer authority path: $relative"
    }
    $candidate = Assert-ContainedRegularPath -Root $repoFull -Path (
        Join-Path $repoFull $relative.Replace('/', [System.IO.Path]::DirectorySeparatorChar)
    )
    $item = Get-Item -LiteralPath $candidate -Force
    $actualSha256 = Get-LowerSha256 -Path $candidate
    if ($item.Length -ne [long]$entry.bytes -or $actualSha256 -ne [string]$entry.sha256) {
        throw "Finalizer authority identity mismatch: $relative"
    }
    $verified.Add([ordered]@{
        bytes = [long]$item.Length
        path = $relative
        sha256 = $actualSha256
    })
}
if ($verified.Count -eq 0) {
    throw 'Comparison-finalizer authority has no files'
}

# This reproduces Python's canonical JSON: sorted object keys, compact UTF-8,
# and one trailing newline. Property insertion below is bytes/path/sha256.
$inventoryJson = @($verified) | ConvertTo-Json -Depth 4 -Compress
$inventoryBytes = [System.Text.UTF8Encoding]::new($false).GetBytes($inventoryJson + "`n")
$prefixBytes = [System.Text.UTF8Encoding]::new($false).GetBytes(
    "phase40-comparison-finalizer-source-v1`0"
)
$treeSha256 = Get-CombinedSha256 -Prefix $prefixBytes -Payload $inventoryBytes
if ($treeSha256 -ne [string]$authority.source_tree_sha256) {
    throw "Finalizer source-tree hash mismatch: expected=$($authority.source_tree_sha256) actual=$treeSha256"
}

$receipt = [ordered]@{
    schema_version = 'phase40-comparison-authority-preflight-v1'
    status = 'PASS'
    verified_at_utc = [DateTime]::UtcNow.ToString('o')
    amendment_sha256 = $amendmentSha256
    request_sha256 = $requestSha256
    source_tree_sha256 = $treeSha256
    preflight_script_path = $PSCommandPath
    preflight_script_sha256 = Get-LowerSha256 -Path $PSCommandPath
    verified_file_count = $verified.Count
    verified_files = @($verified)
    python_launched = $false
    model_bundle_opened = $false
    reserved_split_access_attempted = $false
}
$receiptJson = $receipt | ConvertTo-Json -Depth 6
Write-ExclusiveUtf8 -Path $outputFull -Text ($receiptJson + "`n")
Write-Output "PASS comparison authority files=$($verified.Count) receipt=$outputFull"
