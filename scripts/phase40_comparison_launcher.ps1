[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$ReceiptSchema = 'phase40-comparison-launch-receipt-v1'
$RequestRelative = 'data/models/phase40/full-run-request.json'
$AmendmentRelative = 'data/models/phase40/two-full-model-scope-amendment.json'
$ReceiptRelative = 'data/models/phase40/comparison-launch-receipt.json'
$LauncherRelative = 'scripts/phase40_comparison_launcher.ps1'
$TreeDomain = "phase40-comparison-finalizer-source-v1`0"
$AllowedHostSha256 = '057a2754877cd356159ea891883179f8620ffdc89d3c70d2c4d1f3ba3f6c49b0'
$AllowedHostVersion = '7.6.1'
$AllowedPythonSha256 = 'dc7ecf75280678175b4f931ce05f1ef9c10d48984399ca7de6beee69d71bcb1b'
$AllowedPythonVersion = '3.13.13'
$ExpectedActiveRunIds = @(
    'phase40-qwen-qlora-full-seed42-v1',
    'phase40-phobert-full-seed42-v1'
)
$ExpectedActiveRoots = @(
    'data/models/phase40/full/qwen-qlora',
    'data/models/phase40/full/phobert'
)
$ExpectedFinalizerSourcePaths = @(
    'pyproject.toml',
    'src/__init__.py',
    'src/config/__init__.py',
    'src/config/settings.py',
    'src/data_pipeline/__init__.py',
    'src/data_pipeline/processing/__init__.py',
    'src/data_pipeline/processing/normalizer.py',
    'src/data_pipeline/schemas.py',
    'src/model_adaptation/__init__.py',
    'src/model_adaptation/catalog.py',
    'src/model_adaptation/cli.py',
    'src/model_adaptation/convert.py',
    'src/model_adaptation/data.py',
    'src/model_adaptation/doctor.py',
    'src/model_adaptation/explanation_review.py',
    'src/model_adaptation/phase40_callbacks.py',
    'src/model_adaptation/phase40_contract.py',
    'src/model_adaptation/phase40_evidence.py',
    'src/model_adaptation/phase40_graphs.py',
    'src/model_adaptation/phase40_handoff.py',
    'src/model_adaptation/phase40_metrics.py',
    'src/model_adaptation/phase40_modes.py',
    'src/model_adaptation/phase40_notebooks.py',
    'src/model_adaptation/pilot.py',
    'src/model_adaptation/prompts.py',
    'src/model_adaptation/registry.py',
    'src/model_adaptation/release_evaluation.py',
    'src/model_adaptation/release_gates.py',
    'src/model_adaptation/release_readiness.py',
    'src/model_adaptation/schemas.py',
    'src/model_adaptation/training.py',
    'src/runtime/__init__.py',
    'src/runtime/analyzers/__init__.py',
    'src/runtime/analyzers/accelerated.py',
    'src/runtime/analyzers/base.py',
    'src/runtime/analyzers/gguf.py',
    'src/runtime/analyzers/heuristic.py',
    'src/runtime/analyzers/local_model.py',
    'src/runtime/analyzers/rules.py',
    'src/runtime/contracts.py',
    'src/runtime/service.py'
)
$FinalizerArguments = @(
    '-s',
    '-B',
    '-m',
    'src.model_adaptation.cli',
    'phase40-finalize-comparison',
    '--request-path',
    $RequestRelative,
    '--scope-amendment-path',
    $AmendmentRelative,
    '--repo-root',
    '.',
    '--output-root',
    'data/models/phase40',
    '--bundle-root',
    'phase40-qwen-qlora-full-seed42-v1=data/models/phase40/full/qwen-qlora',
    '--bundle-root',
    'phase40-phobert-full-seed42-v1=data/models/phase40/full/phobert',
    '--gpu-identity',
    'phase40-qwen-qlora-full-seed42-v1=NVIDIA GeForce RTX 5050 Laptop GPU',
    '--gpu-identity',
    'phase40-phobert-full-seed42-v1=NVIDIA GeForce RTX 5050 Laptop GPU'
)

function Get-LowerSha256Bytes {
    param(
        [Parameter(Mandatory = $true)]
        [AllowEmptyCollection()]
        [byte[]]$Payload
    )
    return [System.Convert]::ToHexString(
        [System.Security.Cryptography.SHA256]::HashData($Payload)
    ).ToLowerInvariant()
}

function Get-LowerSha256Text {
    param([Parameter(Mandatory = $true)][string]$Text)
    return Get-LowerSha256Bytes -Payload (
        [System.Text.UTF8Encoding]::new($false).GetBytes($Text)
    )
}

function Get-CombinedSha256 {
    param(
        [Parameter(Mandatory = $true)][byte[]]$Prefix,
        [Parameter(Mandatory = $true)][byte[]]$Payload
    )
    $Combined = [byte[]]::new($Prefix.Length + $Payload.Length)
    [System.Buffer]::BlockCopy($Prefix, 0, $Combined, 0, $Prefix.Length)
    [System.Buffer]::BlockCopy($Payload, 0, $Combined, $Prefix.Length, $Payload.Length)
    return Get-LowerSha256Bytes -Payload $Combined
}

function Assert-NoDuplicateJsonProperties {
    param(
        [Parameter(Mandatory = $true)][System.Text.Json.JsonElement]$Element,
        [string]$Context = '$'
    )
    if ($Element.ValueKind -eq [System.Text.Json.JsonValueKind]::Object) {
        $Names = [System.Collections.Generic.HashSet[string]]::new(
            [System.StringComparer]::Ordinal
        )
        foreach ($Property in $Element.EnumerateObject()) {
            foreach ($Character in $Property.Name.ToCharArray()) {
                if ([char]::IsSurrogate($Character)) {
                    throw "Supplementary Unicode JSON property names are forbidden at $Context"
                }
            }
            if (-not $Names.Add($Property.Name)) {
                throw "Duplicate JSON property at ${Context}: $($Property.Name)"
            }
            Assert-NoDuplicateJsonProperties `
                -Element $Property.Value `
                -Context "${Context}.$($Property.Name)"
        }
    }
    elseif ($Element.ValueKind -eq [System.Text.Json.JsonValueKind]::Array) {
        $Index = 0
        foreach ($Item in $Element.EnumerateArray()) {
            Assert-NoDuplicateJsonProperties -Element $Item -Context "${Context}[$Index]"
            $Index++
        }
    }
}

function ConvertTo-PythonCanonicalJsonNumber {
    param(
        [Parameter(Mandatory = $true)]
        [System.Text.Json.JsonElement]$Element
    )
    $Raw = $Element.GetRawText()
    if ($Raw -cnotmatch '[.eE]') {
        if ($Raw -ceq '-0') {
            return '0'
        }
        return $Raw
    }

    $Invariant = [System.Globalization.CultureInfo]::InvariantCulture
    $Formatted = $Element.GetDouble().ToString('R', $Invariant)
    $Negative = $Formatted.StartsWith('-', [System.StringComparison]::Ordinal)
    $Unsigned = if ($Negative) { $Formatted.Substring(1) } else { $Formatted }
    $Sign = if ($Negative) { '-' } else { '' }

    if ($Unsigned.Contains('E')) {
        $Parts = $Unsigned.Split([char]'E', 2)
        $Mantissa = $Parts[0]
        $Exponent = [int]::Parse(
            $Parts[1],
            [System.Globalization.NumberStyles]::AllowLeadingSign,
            $Invariant
        )
        if ($Exponent -ge -4 -and $Exponent -lt 16) {
            $Digits = $Mantissa.Replace('.', '')
            $DecimalPosition = $Exponent + 1
            if ($DecimalPosition -le 0) {
                $Fixed = '0.' + ('0' * (-$DecimalPosition)) + $Digits
            }
            elseif ($DecimalPosition -ge $Digits.Length) {
                $Fixed = $Digits + ('0' * ($DecimalPosition - $Digits.Length)) + '.0'
            }
            else {
                $Fixed = $Digits.Insert($DecimalPosition, '.')
            }
            return $Sign + $Fixed
        }
        $ExponentSign = if ($Exponent -ge 0) { '+' } else { '-' }
        $ExponentDigits = [Math]::Abs($Exponent).ToString($Invariant).PadLeft(2, '0')
        return $Sign + $Mantissa + 'e' + $ExponentSign + $ExponentDigits
    }

    $Point = $Unsigned.IndexOf('.')
    $IntegerPart = if ($Point -ge 0) { $Unsigned.Substring(0, $Point) } else { $Unsigned }
    $FractionPart = if ($Point -ge 0) { $Unsigned.Substring($Point + 1) } else { '' }
    $CombinedDigits = $IntegerPart + $FractionPart
    $FirstNonzero = -1
    for ($Index = 0; $Index -lt $CombinedDigits.Length; $Index++) {
        if ($CombinedDigits[$Index] -cne '0') {
            $FirstNonzero = $Index
            break
        }
    }
    if ($FirstNonzero -lt 0) {
        return $Sign + '0.0'
    }
    $Exponent = if ($IntegerPart -cne '0') {
        $IntegerPart.Length - 1
    }
    else {
        -($FirstNonzero - $IntegerPart.Length + 1)
    }
    if ($Exponent -ge 16 -or $Exponent -lt -4) {
        $Digits = $CombinedDigits.Substring($FirstNonzero).TrimEnd([char]'0')
        $Mantissa = $Digits.Substring(0, 1)
        if ($Digits.Length -gt 1) {
            $Mantissa += '.' + $Digits.Substring(1)
        }
        $ExponentSign = if ($Exponent -ge 0) { '+' } else { '-' }
        $ExponentDigits = [Math]::Abs($Exponent).ToString($Invariant).PadLeft(2, '0')
        return $Sign + $Mantissa + 'e' + $ExponentSign + $ExponentDigits
    }
    if ($Point -lt 0) {
        return $Formatted + '.0'
    }
    return $Formatted
}

function Write-CanonicalJsonElement {
    param(
        [Parameter(Mandatory = $true)][System.Text.Json.JsonElement]$Element,
        [Parameter(Mandatory = $true)][System.Text.Json.Utf8JsonWriter]$Writer
    )
    switch ($Element.ValueKind) {
        ([System.Text.Json.JsonValueKind]::Object) {
            $Writer.WriteStartObject()
            [string[]]$Names = @(
                $Element.EnumerateObject() | ForEach-Object { $_.Name }
            )
            [Array]::Sort($Names, [System.StringComparer]::Ordinal)
            foreach ($Name in $Names) {
                $Writer.WritePropertyName($Name)
                $Child = $Element.GetProperty($Name)
                Write-CanonicalJsonElement -Element $Child -Writer $Writer
            }
            $Writer.WriteEndObject()
        }
        ([System.Text.Json.JsonValueKind]::Array) {
            $Writer.WriteStartArray()
            foreach ($Item in $Element.EnumerateArray()) {
                Write-CanonicalJsonElement -Element $Item -Writer $Writer
            }
            $Writer.WriteEndArray()
        }
        ([System.Text.Json.JsonValueKind]::String) {
            $Writer.WriteStringValue($Element.GetString())
        }
        ([System.Text.Json.JsonValueKind]::Number) {
            $CanonicalNumber = ConvertTo-PythonCanonicalJsonNumber -Element $Element
            $Writer.WriteRawValue($CanonicalNumber, $false)
        }
        ([System.Text.Json.JsonValueKind]::True) {
            $Writer.WriteBooleanValue($true)
        }
        ([System.Text.Json.JsonValueKind]::False) {
            $Writer.WriteBooleanValue($false)
        }
        ([System.Text.Json.JsonValueKind]::Null) {
            $Writer.WriteNullValue()
        }
        default {
            throw "Unsupported JSON value kind: $($Element.ValueKind)"
        }
    }
}

function Convert-JsonDocumentToCanonicalBytes {
    param([Parameter(Mandatory = $true)][System.Text.Json.JsonDocument]$Document)
    $Stream = [System.IO.MemoryStream]::new()
    $Options = [System.Text.Json.JsonWriterOptions]::new()
    $Options.Indented = $false
    $Options.SkipValidation = $false
    $Options.Encoder = [System.Text.Encodings.Web.JavaScriptEncoder]::UnsafeRelaxedJsonEscaping
    $Writer = [System.Text.Json.Utf8JsonWriter]::new($Stream, $Options)
    try {
        Write-CanonicalJsonElement -Element $Document.RootElement -Writer $Writer
        $Writer.Flush()
        $Raw = $Stream.ToArray()
        $Result = [byte[]]::new($Raw.Length + 1)
        [System.Buffer]::BlockCopy($Raw, 0, $Result, 0, $Raw.Length)
        $Result[$Raw.Length] = 10
        return $Result
    }
    finally {
        $Writer.Dispose()
        $Stream.Dispose()
    }
}

function ConvertTo-CanonicalJsonBytes {
    param([Parameter(Mandatory = $true)]$Value)
    $Text = ConvertTo-Json -InputObject $Value -Depth 100 -Compress
    $Options = [System.Text.Json.JsonDocumentOptions]::new()
    $Options.AllowTrailingCommas = $false
    $Options.CommentHandling = [System.Text.Json.JsonCommentHandling]::Disallow
    $Document = [System.Text.Json.JsonDocument]::Parse($Text, $Options)
    try {
        Assert-NoDuplicateJsonProperties -Element $Document.RootElement
        return Convert-JsonDocumentToCanonicalBytes -Document $Document
    }
    finally {
        $Document.Dispose()
    }
}

function ConvertFrom-StrictCanonicalJsonBytes {
    param(
        [Parameter(Mandatory = $true)][byte[]]$Payload,
        [Parameter(Mandatory = $true)][string]$Description
    )
    try {
        $Text = [System.Text.UTF8Encoding]::new($false, $true).GetString($Payload)
        $Options = [System.Text.Json.JsonDocumentOptions]::new()
        $Options.AllowTrailingCommas = $false
        $Options.CommentHandling = [System.Text.Json.JsonCommentHandling]::Disallow
        $Document = [System.Text.Json.JsonDocument]::Parse($Text, $Options)
    }
    catch {
        throw "$Description is not strict UTF-8 JSON: $($_.Exception.Message)"
    }
    try {
        if ($Document.RootElement.ValueKind -ne [System.Text.Json.JsonValueKind]::Object) {
            throw "$Description must be one JSON object"
        }
        Assert-NoDuplicateJsonProperties -Element $Document.RootElement
        $Canonical = Convert-JsonDocumentToCanonicalBytes -Document $Document
        if ([System.Convert]::ToBase64String($Canonical) -cne
            [System.Convert]::ToBase64String($Payload)) {
            throw "$Description must be canonical JSON"
        }
    }
    finally {
        $Document.Dispose()
    }
    return ConvertFrom-Json -InputObject $Text -AsHashtable -Depth 100
}

function Assert-ExactKeys {
    param(
        [Parameter(Mandatory = $true)][System.Collections.IDictionary]$Value,
        [Parameter(Mandatory = $true)][string[]]$Expected,
        [Parameter(Mandatory = $true)][string]$Description
    )
    $ActualKeys = @($Value.Keys | ForEach-Object { [string]$_ } | Sort-Object -CaseSensitive)
    $ExpectedKeys = @($Expected | Sort-Object -CaseSensitive)
    if ([string]::Join("`0", $ActualKeys) -cne [string]::Join("`0", $ExpectedKeys)) {
        throw "$Description keys mismatch"
    }
}

function Assert-CanonicalLowerSha256 {
    param(
        [Parameter(Mandatory = $true)]
        [AllowNull()]
        [object]$Value,
        [Parameter(Mandatory = $true)]
        [string]$Description
    )
    if (-not ($Value -is [string]) -or
        [string]$Value -cnotmatch '^[0-9a-f]{64}$') {
        throw "$Description must be a canonical lowercase SHA-256"
    }
    return [string]$Value
}

function Assert-SafeFinalizerSourcePath {
    param(
        [Parameter(Mandatory = $true)]
        [AllowNull()]
        [object]$Value
    )
    if (-not ($Value -is [string])) {
        throw 'Comparison source path must be a string'
    }
    $Relative = [string]$Value
    if ([string]::IsNullOrEmpty($Relative) -or
        $Relative.Contains('\') -or
        $Relative.Contains([char]0) -or
        $Relative.StartsWith('/', [System.StringComparison]::Ordinal) -or
        $Relative.EndsWith('/', [System.StringComparison]::Ordinal) -or
        $Relative.Contains('//') -or
        [System.IO.Path]::IsPathRooted($Relative)) {
        throw "Comparison source path is not canonical POSIX relative: $Relative"
    }
    $Segments = $Relative.Split(
        [char]'/',
        [System.StringSplitOptions]::None
    )
    foreach ($Segment in $Segments) {
        if ([string]::IsNullOrEmpty($Segment) -or
            $Segment -ceq '.' -or
            $Segment -ceq '..' -or
            $Segment.Contains(':')) {
            throw "Comparison source path is not canonical POSIX relative: $Relative"
        }
        foreach ($Character in $Segment.ToCharArray()) {
            if ([int]$Character -lt 32) {
                throw "Comparison source path contains a control character"
            }
        }
    }
    $InAllowedNamespace = $Relative -ceq 'pyproject.toml' -or (
        $Segments.Count -ge 2 -and
        $Segments[0] -ceq 'src' -and
        $Segments[$Segments.Count - 1].EndsWith(
            '.py',
            [System.StringComparison]::Ordinal
        )
    )
    if (-not $InAllowedNamespace) {
        throw "Comparison source path leaves the allowed Python source namespace: $Relative"
    }
    return $Relative
}

function Assert-NoReparseAncestors {
    param([Parameter(Mandatory = $true)][string]$Path)
    $Current = Get-Item -LiteralPath ([System.IO.Path]::GetFullPath($Path)) -Force
    while ($null -ne $Current) {
        if (($Current.Attributes -band [System.IO.FileAttributes]::ReparsePoint) -ne 0) {
            throw "Authority path contains a reparse point: $($Current.FullName)"
        }
        $Current = if (
            ($Current.Attributes -band [System.IO.FileAttributes]::Directory) -ne 0
        ) {
            $Current.Parent
        }
        else {
            $Current.Directory
        }
    }
}

function Assert-ContainedRegularPath {
    param(
        [Parameter(Mandatory = $true)][string]$Root,
        [Parameter(Mandatory = $true)][string]$Path,
        [switch]$AllowMissingLeaf
    )
    $RootFull = [System.IO.Path]::GetFullPath($Root).TrimEnd(
        [System.IO.Path]::DirectorySeparatorChar
    )
    $PathFull = [System.IO.Path]::GetFullPath($Path)
    $Prefix = $RootFull + [System.IO.Path]::DirectorySeparatorChar
    if ($PathFull -cne $RootFull -and
        -not $PathFull.StartsWith($Prefix, [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "Authority path escaped repository root: $PathFull"
    }
    $Current = if ($AllowMissingLeaf -and -not (Test-Path -LiteralPath $PathFull)) {
        [System.IO.Path]::GetDirectoryName($PathFull)
    }
    else {
        $PathFull
    }
    while ($true) {
        $Item = Get-Item -LiteralPath $Current -Force
        if (($Item.Attributes -band [System.IO.FileAttributes]::ReparsePoint) -ne 0) {
            throw "Authority path contains a reparse point: $Current"
        }
        if ($Current.Equals($RootFull, [System.StringComparison]::OrdinalIgnoreCase)) {
            break
        }
        $Parent = [System.IO.Path]::GetDirectoryName($Current)
        if (-not $Parent -or $Parent.Equals($Current, [System.StringComparison]::OrdinalIgnoreCase)) {
            throw "Authority path did not reach repository root: $PathFull"
        }
        $Current = $Parent
    }
    if (-not $AllowMissingLeaf) {
        $Leaf = Get-Item -LiteralPath $PathFull -Force
        if ($Leaf.PSIsContainer -or
            ($Leaf.Attributes -band [System.IO.FileAttributes]::ReparsePoint) -ne 0) {
            throw "Authority source is not one regular file: $PathFull"
        }
    }
    return $PathFull
}

function Open-LockedReadFile {
    param([Parameter(Mandatory = $true)][string]$Path)
    $FullPath = [System.IO.Path]::GetFullPath($Path)
    Assert-NoReparseAncestors -Path $FullPath
    $Stream = [System.IO.File]::Open(
        $FullPath,
        [System.IO.FileMode]::Open,
        [System.IO.FileAccess]::Read,
        [System.IO.FileShare]::Read
    )
    try {
        if ($Stream.Length -gt [int]::MaxValue) {
            throw "Authority file is too large: $FullPath"
        }
        $Payload = [byte[]]::new([int]$Stream.Length)
        $Offset = 0
        while ($Offset -lt $Payload.Length) {
            $Read = $Stream.Read($Payload, $Offset, $Payload.Length - $Offset)
            if ($Read -le 0) {
                throw "Authority file ended early: $FullPath"
            }
            $Offset += $Read
        }
        $Stream.Position = 0
        return [PSCustomObject]@{
            Path = $FullPath
            Stream = $Stream
            Payload = $Payload
            Bytes = [long]$Payload.Length
            Sha256 = Get-LowerSha256Bytes -Payload $Payload
        }
    }
    catch {
        $Stream.Dispose()
        throw
    }
}

function Write-ExclusiveBytes {
    param(
        [Parameter(Mandatory = $true)][string]$Path,
        [Parameter(Mandatory = $true)][byte[]]$Payload
    )
    try {
        $Stream = [System.IO.FileStream]::new(
            $Path,
            [System.IO.FileMode]::CreateNew,
            [System.IO.FileAccess]::Write,
            [System.IO.FileShare]::None,
            4096,
            [System.IO.FileOptions]::WriteThrough
        )
    }
    catch [System.IO.IOException] {
        throw "Refusing to overwrite or race comparison-launch receipt: $Path"
    }
    try {
        $Stream.Write($Payload, 0, $Payload.Length)
        $Stream.Flush($true)
    }
    finally {
        $Stream.Dispose()
    }
}

function Get-PortablePathSha256 {
    param([Parameter(Mandatory = $true)][string]$Path)
    $Normalized = [System.IO.Path]::GetFullPath($Path).ToLowerInvariant().Replace('\', '/')
    return Get-LowerSha256Text -Text $Normalized
}

function Format-CanonicalUtcTimestamp {
    param([Parameter(Mandatory = $true)][DateTime]$Value)
    $Utc = $Value.ToUniversalTime()
    $MicrosecondTicks = $Utc.Ticks - ($Utc.Ticks % 10)
    $CanonicalUtc = [DateTime]::new($MicrosecondTicks, [DateTimeKind]::Utc)
    $Format = if (($CanonicalUtc.Ticks % [TimeSpan]::TicksPerSecond) -eq 0) {
        "yyyy-MM-ddTHH:mm:ss'Z'"
    }
    else {
        "yyyy-MM-ddTHH:mm:ss.ffffff'Z'"
    }
    return $CanonicalUtc.ToString(
        $Format,
        [System.Globalization.CultureInfo]::InvariantCulture
    )
}

function Get-CanonicalUtcNow {
    return Format-CanonicalUtcTimestamp -Value ([DateTime]::UtcNow)
}

function ConvertFrom-CanonicalUtcTimestamp {
    param([Parameter(Mandatory = $true)][string]$Value)
    return [DateTime]::ParseExact(
        $Value,
        [string[]]@(
            "yyyy-MM-ddTHH:mm:ss'Z'",
            "yyyy-MM-ddTHH:mm:ss.ffffff'Z'"
        ),
        [System.Globalization.CultureInfo]::InvariantCulture,
        (
            [System.Globalization.DateTimeStyles]::AssumeUniversal -bor
            [System.Globalization.DateTimeStyles]::AdjustToUniversal
        )
    )
}

function Test-StringArrayEqual {
    param(
        [Parameter(Mandatory = $true)]$Actual,
        [Parameter(Mandatory = $true)][string[]]$Expected
    )
    if (-not ($Actual -is [object[]]) -or $Actual.Count -ne $Expected.Count) {
        return $false
    }
    for ($Index = 0; $Index -lt $Expected.Count; $Index++) {
        if (-not ($Actual[$Index] -is [string]) -or
            [string]$Actual[$Index] -cne $Expected[$Index]) {
            return $false
        }
    }
    return $true
}

$PreflightStartedAtUtc = Get-CanonicalUtcNow
$LauncherPath = [System.IO.Path]::GetFullPath($PSCommandPath)
if ([System.IO.Path]::GetFileName($LauncherPath) -cne 'phase40_comparison_launcher.ps1') {
    throw 'Comparison launcher filename drifted'
}
$LauncherDirectory = [System.IO.Path]::GetDirectoryName($LauncherPath)
if ([System.IO.Path]::GetFileName($LauncherDirectory) -cne 'scripts') {
    throw 'Comparison launcher is outside its fixed repository scripts directory'
}
$RepositoryRoot = [System.IO.Directory]::GetParent(
    $LauncherDirectory
).FullName
if (-not (Test-Path -LiteralPath $RepositoryRoot -PathType Container)) {
    throw 'Comparison launcher repository root is missing'
}
$ExpectedLauncherPath = [System.IO.Path]::GetFullPath(
    (Join-Path $RepositoryRoot $LauncherRelative)
)
if (-not $LauncherPath.Equals(
    $ExpectedLauncherPath,
    [System.StringComparison]::OrdinalIgnoreCase
)) {
    throw 'Comparison launcher actual path differs from its fixed repository location'
}
Assert-NoReparseAncestors -Path $RepositoryRoot

$Locks = [System.Collections.Generic.List[System.IDisposable]]::new()
$OldPythonPath = $env:PYTHONPATH
$OldPythonHome = $env:PYTHONHOME
$OldNoUserSite = $env:PYTHONNOUSERSITE
try {
    $LauncherLock = Open-LockedReadFile -Path $LauncherPath
    $Locks.Add($LauncherLock.Stream)

    $RequestPath = Assert-ContainedRegularPath -Root $RepositoryRoot -Path (
        Join-Path $RepositoryRoot $RequestRelative
    )
    $AmendmentPath = Assert-ContainedRegularPath -Root $RepositoryRoot -Path (
        Join-Path $RepositoryRoot $AmendmentRelative
    )
    $ReceiptPath = Assert-ContainedRegularPath -Root $RepositoryRoot -Path (
        Join-Path $RepositoryRoot $ReceiptRelative
    ) -AllowMissingLeaf
    if (Test-Path -LiteralPath $ReceiptPath) {
        throw 'Refusing to overwrite frozen comparison-launch receipt'
    }

    $RequestLock = Open-LockedReadFile -Path $RequestPath
    $Locks.Add($RequestLock.Stream)
    $AmendmentLock = Open-LockedReadFile -Path $AmendmentPath
    $Locks.Add($AmendmentLock.Stream)
    $Request = ConvertFrom-StrictCanonicalJsonBytes `
        -Payload $RequestLock.Payload `
        -Description 'Canonical Phase 40 run request'
    $Amendment = ConvertFrom-StrictCanonicalJsonBytes `
        -Payload $AmendmentLock.Payload `
        -Description 'Canonical Phase 40 scope amendment'

    Assert-ExactKeys -Value $Request -Expected @(
        'schema_version', 'runs', 'source_bundle', 'input_bundle',
        'package_candidates', 'expected_bundle_files', 'control_template_by_run',
        'control_template_digest_by_run', 'no_held_out_boundary', 'git_commit'
    ) -Description 'Phase 40 run request'
    if (-not ($Request.schema_version -is [string]) -or
        $Request.schema_version -cne 'phase40-full-run-request-v1' -or
        -not ($Request.no_held_out_boundary -is [bool]) -or
        $Request.no_held_out_boundary -ne $true) {
        throw 'Phase 40 run-request schema or held-out boundary drifted'
    }
    Assert-ExactKeys -Value $Amendment -Expected @(
        'schema_version', 'original_run_request_path',
        'original_run_request_sha256', 'active_full_run_ids',
        'active_returned_roots', 'waived_full_run_id', 'waived_returned_root',
        'full_lora_disposition', 'waiver_action', 'waiver_basis',
        'lora_probe_authority', 'comparison_finalizer_authority',
        'quality_model_run_ids', 'review_model_run_ids', 'execution_policy',
        'colab_contingency_policy', 'no_held_out_boundary'
    ) -Description 'Phase 40 scope amendment'
    $BoundRequestSha256 = Assert-CanonicalLowerSha256 `
        -Value $Amendment.original_run_request_sha256 `
        -Description 'Scope-amendment run-request hash'
    if (-not ($Amendment.schema_version -is [string]) -or
        $Amendment.schema_version -cne 'phase40-two-full-model-scope-amendment-v1' -or
        -not ($Amendment.original_run_request_path -is [string]) -or
        $Amendment.original_run_request_path -cne $RequestRelative -or
        $BoundRequestSha256 -cne $RequestLock.Sha256) {
        throw 'Scope amendment does not bind the exact canonical run request'
    }
    if (-not (Test-StringArrayEqual $Amendment.active_full_run_ids $ExpectedActiveRunIds) -or
        -not (Test-StringArrayEqual $Amendment.quality_model_run_ids $ExpectedActiveRunIds) -or
        -not (Test-StringArrayEqual $Amendment.review_model_run_ids $ExpectedActiveRunIds) -or
        -not (Test-StringArrayEqual $Amendment.active_returned_roots $ExpectedActiveRoots) -or
        $Amendment.waived_full_run_id -cne 'phase40-qwen-lora-full-seed42-v1' -or
        $Amendment.waived_returned_root -cne 'data/models/phase40/full/qwen-lora' -or
        $Amendment.full_lora_disposition -cne 'cancelled_before_start' -or
        $Amendment.waiver_action -cne 'withdrawn' -or
        $Amendment.waiver_basis -cne 'bounded_local_probe_established_resource_pressure_and_deadline_mismatch' -or
        $Amendment.execution_policy -cne 'local_primary' -or
        $Amendment.colab_contingency_policy -cne 'validation_only_before_held_out_open_if_local_quality_unacceptable' -or
        -not ($Amendment.no_held_out_boundary -is [bool]) -or
        $Amendment.no_held_out_boundary -ne $true) {
        throw 'Phase 40 scope-amendment policy or model set drifted'
    }

    $Authority = $Amendment.comparison_finalizer_authority
    Assert-ExactKeys -Value $Authority -Expected @(
        'schema_version', 'runtime_origin', 'files', 'source_tree_sha256'
    ) -Description 'Comparison-finalizer authority'
    if (-not ($Authority.schema_version -is [string]) -or
        $Authority.schema_version -cne 'phase40-comparison-finalizer-authority-v1' -or
        -not ($Authority.runtime_origin -is [string]) -or
        $Authority.runtime_origin -cne 'local_hash_pinned_source_not_training_runtime_v3') {
        throw 'Comparison-finalizer authority schema or origin drifted'
    }
    $BoundSourceTreeSha256 = Assert-CanonicalLowerSha256 `
        -Value $Authority.source_tree_sha256 `
        -Description 'Comparison-finalizer source-tree hash'
    if (-not ($Authority.files -is [object[]]) -or
        $Authority.files.Count -ne $ExpectedFinalizerSourcePaths.Count) {
        throw 'Comparison-finalizer files must be the exact code-fixed source array'
    }

    # Validate the complete declared namespace and raw JSON token shapes before
    # any source path is statted or opened.  A hostile late entry therefore
    # cannot trigger reads of earlier valid entries or any reserved data path.
    $DeclaredFiles = [System.Collections.Generic.List[object]]::new()
    for ($Index = 0; $Index -lt $Authority.files.Count; $Index++) {
        $Entry = $Authority.files[$Index]
        if (-not ($Entry -is [System.Collections.IDictionary])) {
            throw "Comparison source entry $Index must be one JSON object"
        }
        Assert-ExactKeys -Value $Entry -Expected @('path', 'bytes', 'sha256') `
            -Description 'Comparison source entry'
        $Relative = Assert-SafeFinalizerSourcePath -Value $Entry.path
        if ($Relative -cne $ExpectedFinalizerSourcePaths[$Index]) {
            throw 'Comparison source inventory differs from the code-fixed source allowlist'
        }
        if (-not ($Entry.bytes -is [long]) -or [long]$Entry.bytes -lt 0) {
            throw "Comparison source byte count is not a nonnegative integer: $Relative"
        }
        $EntrySha256 = Assert-CanonicalLowerSha256 `
            -Value $Entry.sha256 `
            -Description "Comparison source SHA-256 for $Relative"
        $DeclaredFiles.Add([ordered]@{
            path = $Relative
            bytes = [long]$Entry.bytes
            sha256 = $EntrySha256
        })
    }
    $DeclaredFileArray = [object[]]$DeclaredFiles.ToArray()
    $RawInventoryBytes = ConvertTo-CanonicalJsonBytes -Value $Authority.files
    $DeclaredInventoryBytes = ConvertTo-CanonicalJsonBytes -Value $DeclaredFileArray
    if ([System.Convert]::ToBase64String($RawInventoryBytes) -cne
        [System.Convert]::ToBase64String($DeclaredInventoryBytes)) {
        throw 'Comparison source inventory uses noncanonical JSON token types'
    }
    $TreeSha256 = Get-CombinedSha256 -Prefix (
        [System.Text.UTF8Encoding]::new($false).GetBytes($TreeDomain)
    ) -Payload $DeclaredInventoryBytes
    if ($TreeSha256 -cne $BoundSourceTreeSha256) {
        throw 'Comparison-finalizer source-tree hash mismatch'
    }

    $VerifiedFiles = [System.Collections.Generic.List[object]]::new()
    foreach ($Entry in $DeclaredFileArray) {
        $Relative = [string]$Entry.path
        $SourcePath = Assert-ContainedRegularPath -Root $RepositoryRoot -Path (
            Join-Path $RepositoryRoot $Relative.Replace('/', [System.IO.Path]::DirectorySeparatorChar)
        )
        $SourceLock = Open-LockedReadFile -Path $SourcePath
        $Locks.Add($SourceLock.Stream)
        if ($SourceLock.Bytes -ne [long]$Entry.bytes -or
            $SourceLock.Sha256 -cne [string]$Entry.sha256) {
            throw "Comparison source identity mismatch: $Relative"
        }
        $VerifiedFiles.Add([ordered]@{
            path = $Relative
            bytes = $SourceLock.Bytes
            sha256 = $SourceLock.Sha256
        })
    }
    $VerifiedFileArray = [object[]]$VerifiedFiles.ToArray()
    $InventoryBytes = ConvertTo-CanonicalJsonBytes -Value $VerifiedFileArray
    if ([System.Convert]::ToBase64String($InventoryBytes) -cne
        [System.Convert]::ToBase64String($DeclaredInventoryBytes)) {
        throw 'Verified source inventory changed after source locks were acquired'
    }

    $ProgramFiles = [Environment]::GetFolderPath(
        [Environment+SpecialFolder]::ProgramFiles
    )
    $ExpectedHostPath = [System.IO.Path]::GetFullPath(
        (Join-Path $ProgramFiles 'PowerShell\7\pwsh.exe')
    )
    $ActualHostPath = [System.IO.Path]::GetFullPath((Get-Process -Id $PID).Path)
    if (-not $ActualHostPath.Equals(
        $ExpectedHostPath,
        [System.StringComparison]::OrdinalIgnoreCase
    )) {
        throw 'Comparison launcher host path differs from its allowed authority'
    }
    $HostLock = Open-LockedReadFile -Path $ActualHostPath
    $Locks.Add($HostLock.Stream)
    if ($HostLock.Sha256 -cne $AllowedHostSha256 -or
        $PSVersionTable.PSVersion.ToString() -cne $AllowedHostVersion) {
        throw 'Comparison launcher host hash or version differs from its allowed authority'
    }

    $PythonCommand = Get-Command python -CommandType Application -ErrorAction Stop
    $PythonPath = [System.IO.Path]::GetFullPath($PythonCommand.Source)
    if ([System.IO.Path]::GetFileName($PythonPath) -cne 'python.exe') {
        throw 'Canonical Phase 40 Python filename drifted'
    }
    $PythonLock = Open-LockedReadFile -Path $PythonPath
    $Locks.Add($PythonLock.Stream)
    $PythonVersion = (Get-Item -LiteralPath $PythonPath).VersionInfo.ProductVersion
    if ($PythonLock.Sha256 -cne $AllowedPythonSha256 -or
        $PythonVersion -cne $AllowedPythonVersion) {
        throw 'Canonical Phase 40 Python hash or version drifted'
    }

    $PreflightCompletedAtUtc = Get-CanonicalUtcNow
    $ReceiptCreatedAtUtc = Get-CanonicalUtcNow
    $StartedAt = ConvertFrom-CanonicalUtcTimestamp -Value $PreflightStartedAtUtc
    $CompletedAt = ConvertFrom-CanonicalUtcTimestamp -Value $PreflightCompletedAtUtc
    $CreatedAt = ConvertFrom-CanonicalUtcTimestamp -Value $ReceiptCreatedAtUtc
    if ($CompletedAt -lt $StartedAt -or $CreatedAt -lt $CompletedAt) {
        throw 'Comparison-launch receipt chronology is invalid'
    }
    $Core = [ordered]@{
        schema_version = $ReceiptSchema
        status = 'PASS'
        request = [ordered]@{
            relative_path = $RequestRelative
            sha256 = $RequestLock.Sha256
        }
        scope_amendment = [ordered]@{
            relative_path = $AmendmentRelative
            sha256 = $AmendmentLock.Sha256
            original_run_request_sha256 = $RequestLock.Sha256
        }
        finalizer_authority = [ordered]@{
            schema_version = 'phase40-comparison-finalizer-authority-v1'
            runtime_origin = 'local_hash_pinned_source_not_training_runtime_v3'
            files = $VerifiedFileArray
            source_tree_sha256 = $TreeSha256
        }
        launcher = [ordered]@{
            relative_path = $LauncherRelative
            bytes = $LauncherLock.Bytes
            sha256 = $LauncherLock.Sha256
        }
        launcher_host = [ordered]@{
            path_policy = 'windows_known_folder_program_files'
            portable_path = 'PowerShell/7/pwsh.exe'
            path_sha256 = Get-PortablePathSha256 -Path $ActualHostPath
            bytes = $HostLock.Bytes
            sha256 = $HostLock.Sha256
            version = $AllowedHostVersion
        }
        python = [ordered]@{
            path_policy = 'path_resolution_exact_hash'
            portable_path = 'python.exe'
            path_sha256 = Get-PortablePathSha256 -Path $PythonPath
            bytes = $PythonLock.Bytes
            sha256 = $PythonLock.Sha256
            version = $AllowedPythonVersion
        }
        finalizer_command = @('python') + $FinalizerArguments
        preflight_started_at_utc = $PreflightStartedAtUtc
        preflight_completed_at_utc = $PreflightCompletedAtUtc
        receipt_created_at_utc = $ReceiptCreatedAtUtc
        prelaunch_state = [ordered]@{
            python_launched = $false
            model_bundle_opened = $false
            reserved_split_access_attempted = $false
        }
    }
    $CoreBytes = ConvertTo-CanonicalJsonBytes -Value $Core
    $Receipt = [ordered]@{}
    foreach ($Key in $Core.Keys) {
        $Receipt[$Key] = $Core[$Key]
    }
    $Receipt.receipt_sha256 = Get-LowerSha256Bytes -Payload $CoreBytes
    $ReceiptBytes = ConvertTo-CanonicalJsonBytes -Value $Receipt
    Write-ExclusiveBytes -Path $ReceiptPath -Payload $ReceiptBytes
    $ReceiptLock = Open-LockedReadFile -Path $ReceiptPath
    $Locks.Add($ReceiptLock.Stream)
    if ([System.Convert]::ToBase64String($ReceiptLock.Payload) -cne
        [System.Convert]::ToBase64String($ReceiptBytes)) {
        throw 'Comparison-launch receipt changed after durable creation'
    }

    $StartInfo = [System.Diagnostics.ProcessStartInfo]::new()
    $StartInfo.FileName = $PythonPath
    $StartInfo.WorkingDirectory = $RepositoryRoot
    $StartInfo.UseShellExecute = $false
    foreach ($Argument in $FinalizerArguments) {
        [void]$StartInfo.ArgumentList.Add($Argument)
    }
    [void]$StartInfo.Environment.Remove('PYTHONPATH')
    [void]$StartInfo.Environment.Remove('PYTHONHOME')
    $StartInfo.Environment['PYTHONNOUSERSITE'] = '1'
    $Process = [System.Diagnostics.Process]::Start($StartInfo)
    if ($null -eq $Process) {
        throw 'Failed to start the fixed Phase 40 comparison finalizer'
    }
    $Process.WaitForExit()
    $ExitCode = $Process.ExitCode
    $Process.Dispose()
    if ($ExitCode -ne 0) {
        [Console]::Error.WriteLine(
            "Phase 40 comparison finalizer exited with code $ExitCode"
        )
        exit $ExitCode
    }
    Write-Output 'PASS comparison preflight; fixed finalizer completed'
    exit 0
}
finally {
    $env:PYTHONPATH = $OldPythonPath
    $env:PYTHONHOME = $OldPythonHome
    $env:PYTHONNOUSERSITE = $OldNoUserSite
    for ($Index = $Locks.Count - 1; $Index -ge 0; $Index--) {
        $Locks[$Index].Dispose()
    }
}
